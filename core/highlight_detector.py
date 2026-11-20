"""highlight_detector.py: Multi-modal spike detection and highlight ranking engine.
Filters false spikes (giveaways, AFK screens) by evaluating both message velocity and hype density.
"""
import statistics

def is_spike(buckets, i, factor=2.5, min_msgs=8, hist=18, warmup=6):
    """
    Check if bucket i represents a genuine highlight spike compared to recent baseline.
    Returns (is_spike_bool, baseline_count, composite_score).
    """
    if i not in buckets:
        return False, 0, 0.0

    # History window for baseline
    prev_indices = [j for j in range(max(min(buckets.keys(), default=0), i - hist), i) if j in buckets]
    if len(prev_indices) < warmup:
        return False, 0, 0.0

    prev_counts = [len(buckets[j]) for j in prev_indices]
    baseline = max(statistics.median(prev_counts), 1.0)

    current_items = buckets[i]
    current_count = len(current_items)

    # Calculate average hype weight in this bucket
    avg_weight = sum(weight for _, weight in current_items) / max(current_count, 1)

    # Condition: message velocity exceeds factor * baseline, meets minimum count
    velocity_spike = (current_count >= factor * baseline) and (current_count >= min_msgs)
    
    # Composite score incorporates both velocity multiplier and excitement factor
    composite_score = (current_count / baseline) * avg_weight

    return velocity_spike, baseline, composite_score

def top_spikes(buckets, max_clips=10, factor=2.5, min_msgs=8, spacing_buckets=6):
    """
    Select the top N highest-scoring highlight buckets, spaced at least `spacing_buckets` apart.
    """
    scored = []
    for i in sorted(buckets.keys()):
        is_spk, base, score = is_spike(buckets, i, factor=factor, min_msgs=min_msgs)
        if is_spk:
            scored.append((score, i, base, len(buckets[i])))

    # Rank by highest composite score first
    scored.sort(key=lambda x: x[0], reverse=True)

    picked = []
    for score, bucket_idx, base, count in scored:
        if all(abs(bucket_idx - p["bucket"]) >= spacing_buckets for p in picked):
            picked.append({
                "bucket": bucket_idx,
                "score": round(score, 2),
                "count": count,
                "baseline": round(base, 1),
                "messages": [txt for txt, _ in buckets[bucket_idx][:10]]
            })
        if len(picked) == max_clips:
            break

    # Return chronological order
    picked.sort(key=lambda x: x["bucket"])
    return picked
