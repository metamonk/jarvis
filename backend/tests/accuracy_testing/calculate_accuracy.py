#!/usr/bin/env python3
"""
Calculate accuracy metrics from manually reviewed test results.

This script reads the accuracy_review.json file (after manual review)
and calculates the final accuracy percentage.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


def calculate_accuracy_from_reviews(review_file: str) -> Dict[str, Any]:
    """
    Calculate accuracy metrics from reviewed results.

    Args:
        review_file: Path to the accuracy_review.json file

    Returns:
        Dictionary with accuracy metrics
    """
    with open(review_file, 'r') as f:
        data = json.load(f)

    reviews = data.get('reviews', [])

    if not reviews:
        return {
            "error": "No reviews found in file",
            "total_reviews": 0
        }

    # Filter out reviews that have been scored
    scored_reviews = [r for r in reviews if r.get('accuracy_score') is not None]

    if not scored_reviews:
        return {
            "error": "No reviews have been scored yet. Please add accuracy_score values (0-10) to each review.",
            "total_reviews": len(reviews),
            "scored_reviews": 0
        }

    # Calculate metrics
    total_scored = len(scored_reviews)
    total_reviews = len(reviews)
    scores = [r['accuracy_score'] for r in scored_reviews]

    # Overall metrics
    total_score = sum(scores)
    max_possible_score = total_scored * 10
    accuracy_percentage = (total_score / max_possible_score) * 100 if max_possible_score > 0 else 0

    # Score distribution
    score_distribution = {}
    for score in range(11):
        score_distribution[score] = scores.count(score)

    # Category breakdown
    category_stats = {}
    for review in scored_reviews:
        category = review.get('category', 'unknown')
        if category not in category_stats:
            category_stats[category] = {
                "count": 0,
                "total_score": 0,
                "scores": []
            }
        category_stats[category]["count"] += 1
        category_stats[category]["total_score"] += review['accuracy_score']
        category_stats[category]["scores"].append(review['accuracy_score'])

    # Calculate category accuracy
    for category in category_stats:
        count = category_stats[category]["count"]
        total = category_stats[category]["total_score"]
        max_score = count * 10
        category_stats[category]["accuracy_percentage"] = (total / max_score * 100) if max_score > 0 else 0
        category_stats[category]["average_score"] = total / count if count > 0 else 0

    # Perfect scores (10/10)
    perfect_count = scores.count(10)
    perfect_percentage = (perfect_count / total_scored * 100) if total_scored > 0 else 0

    # Good scores (8-10)
    good_count = sum(1 for s in scores if s >= 8)
    good_percentage = (good_count / total_scored * 100) if total_scored > 0 else 0

    # Poor scores (< 6)
    poor_count = sum(1 for s in scores if s < 6)
    poor_percentage = (poor_count / total_scored * 100) if total_scored > 0 else 0

    # Identify problematic queries (score < 8)
    problematic_queries = [
        {
            "query_id": r['query_id'],
            "query": r['query'],
            "category": r['category'],
            "score": r['accuracy_score'],
            "notes": r.get('review_notes', '')
        }
        for r in scored_reviews
        if r['accuracy_score'] < 8
    ]

    return {
        "metadata": {
            "review_file": review_file,
            "calculation_date": datetime.now().isoformat(),
            "target_accuracy": 95.0,
            "target_met": accuracy_percentage >= 95.0
        },
        "overall": {
            "total_queries_reviewed": total_scored,
            "total_queries_in_file": total_reviews,
            "review_completion": (total_scored / total_reviews * 100) if total_reviews > 0 else 0,
            "accuracy_percentage": accuracy_percentage,
            "average_score": sum(scores) / len(scores) if scores else 0,
            "median_score": sorted(scores)[len(scores) // 2] if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0
        },
        "score_breakdown": {
            "perfect_scores_10": {
                "count": perfect_count,
                "percentage": perfect_percentage
            },
            "good_scores_8_to_10": {
                "count": good_count,
                "percentage": good_percentage
            },
            "acceptable_scores_6_to_7": {
                "count": sum(1 for s in scores if 6 <= s < 8),
                "percentage": sum(1 for s in scores if 6 <= s < 8) / total_scored * 100 if total_scored > 0 else 0
            },
            "poor_scores_below_6": {
                "count": poor_count,
                "percentage": poor_percentage
            }
        },
        "score_distribution": score_distribution,
        "category_breakdown": category_stats,
        "problematic_queries": problematic_queries,
        "recommendations": generate_recommendations(accuracy_percentage, problematic_queries, category_stats)
    }


def generate_recommendations(
    accuracy: float,
    problematic_queries: List[Dict],
    category_stats: Dict[str, Any]
) -> List[str]:
    """Generate recommendations based on test results."""
    recommendations = []

    if accuracy >= 95.0:
        recommendations.append("✓ Accuracy target met (≥95%). System performing well.")
    else:
        recommendations.append(f"✗ Accuracy target not met ({accuracy:.2f}% < 95%). Improvement needed.")

    if problematic_queries:
        recommendations.append(
            f"Found {len(problematic_queries)} problematic queries (score < 8). "
            "Review these for common patterns and improve handling."
        )

        # Identify problematic categories
        problem_categories = {}
        for query in problematic_queries:
            cat = query['category']
            problem_categories[cat] = problem_categories.get(cat, 0) + 1

        if problem_categories:
            worst_category = max(problem_categories.items(), key=lambda x: x[1])
            recommendations.append(
                f"Category '{worst_category[0]}' has the most issues ({worst_category[1]} problematic queries). "
                "Focus improvement efforts here."
            )

    # Check category performance
    low_performing_categories = [
        cat for cat, stats in category_stats.items()
        if stats['accuracy_percentage'] < 90.0
    ]

    if low_performing_categories:
        recommendations.append(
            f"Categories with <90% accuracy: {', '.join(low_performing_categories)}. "
            "These need attention."
        )

    if not problematic_queries and accuracy >= 95.0:
        recommendations.append("System is production-ready based on accuracy testing.")

    return recommendations


def print_accuracy_report(metrics: Dict[str, Any]):
    """Print a formatted accuracy report."""
    print("\n" + "=" * 80)
    print("JARVIS ACCURACY TEST RESULTS")
    print("=" * 80)

    if "error" in metrics:
        print(f"\nERROR: {metrics['error']}")
        return

    metadata = metrics['metadata']
    overall = metrics['overall']
    score_breakdown = metrics['score_breakdown']

    print(f"\nTest Date: {metadata['calculation_date']}")
    print(f"Review File: {metadata['review_file']}")
    print(f"\nTarget Accuracy: {metadata['target_accuracy']}%")

    print("\n" + "-" * 80)
    print("OVERALL RESULTS")
    print("-" * 80)
    print(f"Queries Reviewed: {overall['total_queries_reviewed']}/{overall['total_queries_in_file']}")
    print(f"Review Completion: {overall['review_completion']:.1f}%")
    print(f"\nAccuracy: {overall['accuracy_percentage']:.2f}%")
    print(f"Average Score: {overall['average_score']:.2f}/10")
    print(f"Median Score: {overall['median_score']}/10")
    print(f"Score Range: {overall['min_score']}-{overall['max_score']}")

    if metadata['target_met']:
        print("\n✓ ACCURACY TARGET MET (≥95%)")
    else:
        print(f"\n✗ ACCURACY TARGET NOT MET ({overall['accuracy_percentage']:.2f}% < 95%)")

    print("\n" + "-" * 80)
    print("SCORE DISTRIBUTION")
    print("-" * 80)
    print(f"Perfect (10/10): {score_breakdown['perfect_scores_10']['count']} ({score_breakdown['perfect_scores_10']['percentage']:.1f}%)")
    print(f"Good (8-10): {score_breakdown['good_scores_8_to_10']['count']} ({score_breakdown['good_scores_8_to_10']['percentage']:.1f}%)")
    print(f"Acceptable (6-7): {score_breakdown['acceptable_scores_6_to_7']['count']} ({score_breakdown['acceptable_scores_6_to_7']['percentage']:.1f}%)")
    print(f"Poor (<6): {score_breakdown['poor_scores_below_6']['count']} ({score_breakdown['poor_scores_below_6']['percentage']:.1f}%)")

    print("\n" + "-" * 80)
    print("CATEGORY BREAKDOWN")
    print("-" * 80)
    for category, stats in metrics['category_breakdown'].items():
        print(f"\n{category}:")
        print(f"  Count: {stats['count']}")
        print(f"  Accuracy: {stats['accuracy_percentage']:.2f}%")
        print(f"  Average Score: {stats['average_score']:.2f}/10")

    if metrics['problematic_queries']:
        print("\n" + "-" * 80)
        print(f"PROBLEMATIC QUERIES ({len(metrics['problematic_queries'])} queries with score < 8)")
        print("-" * 80)
        for query in metrics['problematic_queries'][:10]:  # Show first 10
            print(f"\n{query['query_id']} (Score: {query['score']}/10)")
            print(f"  Query: {query['query']}")
            print(f"  Category: {query['category']}")
            if query['notes']:
                print(f"  Notes: {query['notes']}")

        if len(metrics['problematic_queries']) > 10:
            print(f"\n... and {len(metrics['problematic_queries']) - 10} more")

    print("\n" + "-" * 80)
    print("RECOMMENDATIONS")
    print("-" * 80)
    for i, rec in enumerate(metrics['recommendations'], 1):
        print(f"{i}. {rec}")

    print("\n" + "=" * 80)


def save_accuracy_report(metrics: Dict[str, Any], output_file: str):
    """Save accuracy report to JSON file."""
    with open(output_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"\nAccuracy report saved to: {output_file}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python calculate_accuracy.py <accuracy_review.json>")
        print("\nExample:")
        print("  python calculate_accuracy.py results/accuracy_review_20251119_120000.json")
        sys.exit(1)

    review_file = sys.argv[1]

    if not Path(review_file).exists():
        print(f"Error: File not found: {review_file}")
        sys.exit(1)

    # Calculate metrics
    metrics = calculate_accuracy_from_reviews(review_file)

    # Print report
    print_accuracy_report(metrics)

    # Save report
    output_file = str(Path(review_file).parent / f"accuracy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    save_accuracy_report(metrics, output_file)


if __name__ == "__main__":
    main()
