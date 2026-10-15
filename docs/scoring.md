# How the scores work

There are two numbers on every hotel card: a **quality score** (0 to 10) and a **value grade** (A to E). They answer different questions.

- Quality: how good do reviewers say this place is?
- Value: compared with everything else in this search, how much hotel do you get for the money?

## Quality score

Code: `backend/src/hotel_watcher/scoring/quality.py`

### 1. Same scale for every source

Each source rates on its own scale. TripAdvisor and Google use 1 to 5, Booking-style sites use 1 to 10. Everything is converted to 0 to 10 first:

```
normalized = rating / scale * 10        # 4.6 / 5 becomes 9.2
```

### 2. Few reviews count for less

A hotel with three 5-star reviews is not better than one with 4.6 stars from 2,000 reviews. To handle that, each rating is pulled toward the average rating of all hotels in the same search, more strongly when it has fewer reviews. This is a Bayesian average:

```
adjusted = (n * normalized + m * area_average) / (n + m)
```

- `n` is the number of reviews behind that rating
- `m` is 50 (`PRIOR_REVIEWS`), meaning the area average is treated as if it were 50 reviews' worth of evidence
- `area_average` is the mean normalized rating across the current results

Examples with an area average of 8.0:

| Rating | Reviews | Adjusted |
|---|---|---|
| 5.0 / 5 | 3 | 8.1 |
| 4.6 / 5 | 2,000 | 9.2 |
| 4.0 / 5 | 40 | 8.0 |

### 3. Sources combined by review count

When a hotel has ratings from several sources (TripAdvisor and Google, say), the adjusted ratings are averaged, weighted by each source's review count. A source with 9,000 reviews outweighs one with 300.

### Labels and confidence

| Score | Label |
|---|---|
| 9.0+ | Exceptional |
| 8.5+ | Excellent |
| 8.0+ | Very good |
| 7.0+ | Good |
| 6.0+ | Fair |
| below | Poor |

Hotels with fewer than 30 reviews in total are marked "few reviews".

## Value grade

Code: `frontend/src/lib/value.ts` (runs in the browser so the slider is instant)

Value only makes sense relative to what else is available, so it uses **percentile ranks within the current search**:

```
quality_pct = rank of the hotel's quality score among the results (0 = lowest, 1 = highest)
price_pct   = rank of its nightly price (0 = cheapest, 1 = most expensive)

value = w * quality_pct + (1 - w) * (1 - price_pct)
```

`w` is the "What matters more" slider: 0 means only price matters, 1 means only quality matters, and the default is 0.5. Ties share their average rank.

| Value | Grade |
|---|---|
| 0.8+ | A |
| 0.6+ | B |
| 0.4+ | C |
| 0.2+ | D |
| below | E |

Hotels without a price or without any reviews get no grade instead of a misleading one.

The price used is the live price for your dates once it has loaded. Until then it is the hotel's typical starting price, which is shown with a dashed pin and "usually from".

## Alerts

Code: `backend/src/hotel_watcher/watch/threshold.py`

- The first check of a new watch sets the baseline. It only alerts if you set a target and the price is already at or under it. Re-adding a watch you removed, or saving it again with a new target, starts a fresh baseline the same way, so a target that is already met is always announced once.
- Prices you saw while browsing before you watched the hotel don't stop that first target alert.
- After that, an alert fires when the price is a **new all-time low for that exact stay** (hotel, dates and number of adults). With a target set, the new low also has to be at or under the target.
- A price that is low but not a new low never alerts again, so the same deal isn't announced on every check.
- All comparisons use the USD price from the provider, never a converted one, so currency movements can't trigger fake "drops".
