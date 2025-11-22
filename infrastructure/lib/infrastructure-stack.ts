import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as elasticache from 'aws-cdk-lib/aws-elasticache';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export interface JarvisStackProps extends cdk.StackProps {
  /**
   * Environment name (dev, staging, prod)
   */
  environment?: string;

  /**
   * Enable CloudFront CDN for static assets
   */
  enableCloudFront?: boolean;

  /**
   * Enable ElastiCache Redis for caching
   */
  enableRedis?: boolean;

  /**
   * Minimum number of ECS tasks
   */
  minTaskCount?: number;

  /**
   * Maximum number of ECS tasks
   */
  maxTaskCount?: number;

  /**
   * Target CPU utilization for auto-scaling
   */
  targetCpuUtilization?: number;
}

export class InfrastructureStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly cluster: ecs.Cluster;
  public readonly database: rds.DatabaseInstance;
  public readonly redis?: elasticache.CfnCacheCluster;
  public readonly cdn?: cloudfront.Distribution;
  public readonly loadBalancer: elbv2.ApplicationLoadBalancer;

  constructor(scope: Construct, id: string, props?: JarvisStackProps) {
    super(scope, id, props);

    const envName = props?.environment || 'dev';
    const enableCloudFront = props?.enableCloudFront ?? true;
    const enableRedis = props?.enableRedis ?? true;
    const minTaskCount = props?.minTaskCount || 2;
    const maxTaskCount = props?.maxTaskCount || 10;
    const targetCpuUtilization = props?.targetCpuUtilization || 70;

    // VPC with public and private subnets
    this.vpc = new ec2.Vpc(this, 'JarvisVpc', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        {
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
        {
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          cidrMask: 24,
        },
        {
          name: 'Isolated',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
          cidrMask: 24,
        },
      ],
    });

    // ECS Cluster
    this.cluster = new ecs.Cluster(this, 'JarvisCluster', {
      vpc: this.vpc,
      clusterName: `jarvis-${envName}`,
      containerInsights: true,
    });

    // RDS PostgreSQL Database
    const dbSecurityGroup = new ec2.SecurityGroup(this, 'DatabaseSecurityGroup', {
      vpc: this.vpc,
      description: 'Security group for Jarvis RDS database',
      allowAllOutbound: true,
    });

    const dbCredentials = new secretsmanager.Secret(this, 'DbCredentials', {
      secretName: `jarvis-${envName}-db-credentials`,
      generateSecretString: {
        secretStringTemplate: JSON.stringify({ username: 'jarvis_admin' }),
        generateStringKey: 'password',
        excludePunctuation: true,
        includeSpace: false,
        passwordLength: 32,
      },
    });

    this.database = new rds.DatabaseInstance(this, 'JarvisDatabase', {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_15_4,
      }),
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T3,
        ec2.InstanceSize.MICRO
      ),
      vpc: this.vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
      },
      securityGroups: [dbSecurityGroup],
      databaseName: 'jarvis',
      credentials: rds.Credentials.fromSecret(dbCredentials),
      allocatedStorage: 20,
      maxAllocatedStorage: 100,
      storageEncrypted: true,
      backupRetention: cdk.Duration.days(7),
      deleteAutomatedBackups: envName !== 'prod',
      removalPolicy: envName === 'prod'
        ? cdk.RemovalPolicy.RETAIN
        : cdk.RemovalPolicy.DESTROY,
      cloudwatchLogsRetention: logs.RetentionDays.ONE_MONTH,
      // Performance optimizations
      parameterGroup: new rds.ParameterGroup(this, 'DbParameterGroup', {
        engine: rds.DatabaseInstanceEngine.postgres({
          version: rds.PostgresEngineVersion.VER_15_4,
        }),
        parameters: {
          'shared_preload_libraries': 'pg_stat_statements',
          'pg_stat_statements.track': 'all',
          'max_connections': '100',
          'effective_cache_size': '256MB',
          'work_mem': '4MB',
        },
      }),
    });

    // ElastiCache Redis for caching
    if (enableRedis) {
      const redisSecurityGroup = new ec2.SecurityGroup(this, 'RedisSecurityGroup', {
        vpc: this.vpc,
        description: 'Security group for Jarvis Redis cache',
        allowAllOutbound: true,
      });

      const redisSubnetGroup = new elasticache.CfnSubnetGroup(
        this,
        'RedisSubnetGroup',
        {
          description: 'Subnet group for Jarvis Redis cache',
          subnetIds: this.vpc.privateSubnets.map((subnet) => subnet.subnetId),
          cacheSubnetGroupName: `jarvis-${envName}-redis`,
        }
      );

      this.redis = new elasticache.CfnCacheCluster(this, 'JarvisRedis', {
        cacheNodeType: 'cache.t3.micro',
        engine: 'redis',
        numCacheNodes: 1,
        vpcSecurityGroupIds: [redisSecurityGroup.securityGroupId],
        cacheSubnetGroupName: redisSubnetGroup.cacheSubnetGroupName,
        engineVersion: '7.0',
        port: 6379,
        clusterName: `jarvis-${envName}`,
        // Performance optimizations
        preferredMaintenanceWindow: 'sun:05:00-sun:06:00',
        snapshotRetentionLimit: envName === 'prod' ? 7 : 1,
      });

      this.redis.addDependency(redisSubnetGroup);

      // Output Redis endpoint
      new cdk.CfnOutput(this, 'RedisEndpoint', {
        value: this.redis.attrRedisEndpointAddress,
        description: 'Redis endpoint address',
        exportName: `jarvis-${envName}-redis-endpoint`,
      });
    }

    // Application Load Balancer
    this.loadBalancer = new elbv2.ApplicationLoadBalancer(this, 'JarvisALB', {
      vpc: this.vpc,
      internetFacing: true,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      loadBalancerName: `jarvis-${envName}-alb`,
    });

    const listener = this.loadBalancer.addListener('HttpListener', {
      port: 80,
      open: true,
    });

    // ECS Task Definition
    const taskDefinition = new ecs.FargateTaskDefinition(
      this,
      'JarvisTaskDef',
      {
        memoryLimitMiB: 2048,
        cpu: 1024,
      }
    );

    // Container definition with performance optimizations
    const container = taskDefinition.addContainer('JarvisContainer', {
      image: ecs.ContainerImage.fromRegistry('nginx:latest'), // Placeholder
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'jarvis',
        logRetention: logs.RetentionDays.ONE_WEEK,
      }),
      environment: {
        NODE_ENV: envName,
        REDIS_URL: enableRedis && this.redis
          ? `redis://${this.redis.attrRedisEndpointAddress}:6379`
          : '',
      },
      secrets: {
        DATABASE_URL: ecs.Secret.fromSecretsManager(dbCredentials),
      },
    });

    container.addPortMappings({
      containerPort: 8080,
      protocol: ecs.Protocol.TCP,
    });

    // ECS Service with auto-scaling
    const service = new ecs.FargateService(this, 'JarvisService', {
      cluster: this.cluster,
      taskDefinition,
      desiredCount: minTaskCount,
      serviceName: `jarvis-${envName}`,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      // Performance optimizations
      healthCheckGracePeriod: cdk.Duration.seconds(60),
      minHealthyPercent: 50,
      maxHealthyPercent: 200,
      circuitBreaker: {
        rollback: true,
      },
    });

    // Allow ECS tasks to access database
    dbSecurityGroup.addIngressRule(
      service.connections.securityGroups[0],
      ec2.Port.tcp(5432),
      'Allow ECS tasks to access database'
    );

    // Allow ECS tasks to access Redis
    if (enableRedis && this.redis) {
      const redisSecurityGroup = ec2.SecurityGroup.fromSecurityGroupId(
        this,
        'ImportedRedisSecurityGroup',
        this.redis.vpcSecurityGroupIds![0]
      );

      service.connections.allowTo(
        redisSecurityGroup,
        ec2.Port.tcp(6379),
        'Allow ECS tasks to access Redis'
      );
    }

    // Target group for load balancer
    const targetGroup = listener.addTargets('JarvisTargetGroup', {
      port: 8080,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [service],
      healthCheck: {
        path: '/health',
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 3,
      },
      deregistrationDelay: cdk.Duration.seconds(30),
    });

    // Auto-scaling configuration
    const scaling = service.autoScaleTaskCount({
      minCapacity: minTaskCount,
      maxCapacity: maxTaskCount,
    });

    // Scale based on CPU utilization
    scaling.scaleOnCpuUtilization('CpuScaling', {
      targetUtilizationPercent: targetCpuUtilization,
      scaleInCooldown: cdk.Duration.seconds(60),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });

    // Scale based on request count
    scaling.scaleOnRequestCount('RequestScaling', {
      requestsPerTarget: 1000,
      targetGroup: targetGroup,
      scaleInCooldown: cdk.Duration.seconds(60),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });

    // S3 bucket for static assets
    const staticAssetsBucket = new s3.Bucket(this, 'StaticAssetsBucket', {
      bucketName: `jarvis-${envName}-static-assets`,
      removalPolicy: envName === 'prod'
        ? cdk.RemovalPolicy.RETAIN
        : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: envName !== 'prod',
      versioned: envName === 'prod',
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    // CloudFront CDN for static assets
    if (enableCloudFront) {
      this.cdn = new cloudfront.Distribution(this, 'JarvisCDN', {
        defaultBehavior: {
          origin: new origins.S3Origin(staticAssetsBucket),
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
          compress: true,
        },
        // Additional behaviors for API endpoints
        additionalBehaviors: {
          '/api/*': {
            origin: new origins.LoadBalancerV2Origin(this.loadBalancer, {
              protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
            }),
            viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
            allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
            compress: true,
          },
        },
        priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
        enableLogging: true,
        comment: `Jarvis ${envName} CDN`,
      });

      // Output CloudFront URL
      new cdk.CfnOutput(this, 'CloudFrontUrl', {
        value: this.cdn.distributionDomainName,
        description: 'CloudFront distribution URL',
        exportName: `jarvis-${envName}-cdn-url`,
      });
    }

    // Outputs
    new cdk.CfnOutput(this, 'LoadBalancerDNS', {
      value: this.loadBalancer.loadBalancerDnsName,
      description: 'Load balancer DNS name',
      exportName: `jarvis-${envName}-alb-dns`,
    });

    new cdk.CfnOutput(this, 'DatabaseEndpoint', {
      value: this.database.dbInstanceEndpointAddress,
      description: 'Database endpoint address',
      exportName: `jarvis-${envName}-db-endpoint`,
    });

    new cdk.CfnOutput(this, 'ClusterName', {
      value: this.cluster.clusterName,
      description: 'ECS cluster name',
      exportName: `jarvis-${envName}-cluster-name`,
    });
  }
}
