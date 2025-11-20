import React, { useEffect, useRef } from 'react';

interface AudioVisualizerProps {
  audioLevel: number; // 0-100
  isActive: boolean;
}

const AudioVisualizer: React.FC<AudioVisualizerProps> = ({ audioLevel, isActive }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | undefined>(undefined);
  const barsRef = useRef<number[]>([]);

  const NUM_BARS = 8;
  const BAR_GAP = 4;
  const MIN_BAR_HEIGHT = 4;
  const SMOOTHING_FACTOR = 0.3;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Initialize bars array if empty
    if (barsRef.current.length === 0) {
      barsRef.current = new Array(NUM_BARS).fill(MIN_BAR_HEIGHT);
    }

    // Set canvas size based on container
    const resizeCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    const animate = () => {
      if (!canvas || !ctx) return;

      const width = canvas.width / window.devicePixelRatio;
      const height = canvas.height / window.devicePixelRatio;

      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      if (!isActive) {
        // Fade out bars when inactive
        barsRef.current = barsRef.current.map(barHeight =>
          Math.max(MIN_BAR_HEIGHT, barHeight * 0.9)
        );
      } else {
        // Calculate target heights based on audio level
        const normalizedLevel = Math.max(0, Math.min(100, audioLevel)) / 100;
        const maxBarHeight = height * 0.8;

        // Update each bar with slight variations for visual interest
        barsRef.current = barsRef.current.map((currentHeight, index) => {
          // Create variation across bars with a wave pattern
          const phase = (index / NUM_BARS) * Math.PI * 2;
          const variation = Math.sin(phase + Date.now() / 200) * 0.2 + 0.8;

          // Calculate target height with variation
          const targetHeight = Math.max(
            MIN_BAR_HEIGHT,
            (normalizedLevel * maxBarHeight * variation)
          );

          // Smooth transition using exponential smoothing
          return currentHeight + (targetHeight - currentHeight) * SMOOTHING_FACTOR;
        });
      }

      // Draw bars
      const barWidth = (width - (NUM_BARS - 1) * BAR_GAP) / NUM_BARS;
      const centerY = height / 2;

      barsRef.current.forEach((barHeight, index) => {
        const x = index * (barWidth + BAR_GAP);
        const y = centerY - barHeight / 2;

        // Create gradient for bars
        const gradient = ctx.createLinearGradient(x, y, x, y + barHeight);

        if (isActive && audioLevel > 5) {
          // Active state - vibrant colors
          gradient.addColorStop(0, '#60a5fa'); // blue-400
          gradient.addColorStop(1, '#3b82f6'); // blue-500
        } else {
          // Inactive/quiet state - muted colors
          gradient.addColorStop(0, '#94a3b8'); // slate-400
          gradient.addColorStop(1, '#64748b'); // slate-500
        }

        ctx.fillStyle = gradient;

        // Draw rounded rectangle for each bar
        const radius = Math.min(barWidth / 2, 3);

        // Custom rounded rectangle drawing (fallback for TypeScript compatibility)
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + barWidth - radius, y);
        ctx.arcTo(x + barWidth, y, x + barWidth, y + radius, radius);
        ctx.lineTo(x + barWidth, y + barHeight - radius);
        ctx.arcTo(x + barWidth, y + barHeight, x + barWidth - radius, y + barHeight, radius);
        ctx.lineTo(x + radius, y + barHeight);
        ctx.arcTo(x, y + barHeight, x, y + barHeight - radius, radius);
        ctx.lineTo(x, y + radius);
        ctx.arcTo(x, y, x + radius, y, radius);
        ctx.closePath();
        ctx.fill();
      });

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animate();

    // Cleanup
    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [audioLevel, isActive]);

  return (
    <div className="w-full h-full flex items-center justify-center">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ maxWidth: '300px', maxHeight: '100px' }}
      />
    </div>
  );
};

export default AudioVisualizer;
