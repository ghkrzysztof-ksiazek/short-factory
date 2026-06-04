# Topic Research Engine — Detailed Specification

## Purpose
Automatically identify emotionally viral relationship psychology topics.

---

# Core Responsibilities

## Discover:
- trending emotional pain points
- controversial opinions
- viral hooks
- repeated emotional themes

---

# Data Sources

## Reddit
High-value subreddits:
- relationship_advice
- dating
- attachment_theory
- breakup
- AskWomen
- AskMen

## YouTube
Collect:
- titles
- views
- comments
- engagement velocity

## TikTok
Collect:
- hooks
- captions
- audio trends
- engagement

---

# Emotional Taxonomy

## Supported Emotions

| Emotion | Importance |
|---|---|
| Curiosity | Critical |
| Fear of loss | Critical |
| Validation | High |
| Loneliness | High |
| Desire | High |
| Rejection | Critical |

---

# Virality Scoring

## Formula Example

```python
score = (
    emotional_intensity * 0.4 +
    controversy * 0.2 +
    relatability * 0.3 +
    novelty * 0.1
)
```

---

# Database Schema

## topics

```sql
CREATE TABLE topics (
    id SERIAL PRIMARY KEY,
    topic TEXT,
    category TEXT,
    emotional_score FLOAT,
    virality_score FLOAT,
    created_at TIMESTAMP
);
```

---

# Example Topic Object

```json
{
  "topic": "Why emotionally unavailable people feel addictive",
  "emotion": "curiosity",
  "category": "attachment_styles",
  "virality_score": 0.92
}
```

---

# Topic Categories

## Recommended Initial Categories
- attachment styles
- texting psychology
- emotional safety
- toxic relationships
- breakups
- masculine/feminine dynamics
- boundaries
- self-worth

---

# Pipeline Flow

```text
Scrape Sources
    ↓
Extract Titles
    ↓
Classify Emotion
    ↓
Score Virality
    ↓
Store in Database
    ↓
Generate Hooks
```

---

# Example Python Scraper

```python
import praw

reddit = praw.Reddit(
    client_id="CLIENT",
    client_secret="SECRET",
    user_agent="factory"
)

posts = reddit.subreddit("dating").hot(limit=50)

for post in posts:
    print(post.title)
```

---

# Future Extensions

## AI Enhancements
- emotional clustering
- trend prediction
- semantic duplicate detection
- retention prediction