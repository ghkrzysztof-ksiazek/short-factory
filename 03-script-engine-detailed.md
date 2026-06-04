# Script Generation Engine — Detailed Specification

## Objective
Generate emotionally engaging short-form scripts optimized for retention.

---

# Content Goals

Every script should:
- stop scrolling
- trigger emotion
- create curiosity
- encourage comments/shares
- fit 30–45 seconds

---

# Required Structure

```text
Hook
→
Emotional Setup
→
Psychological Insight
→
Emotional Resolution
→
CTA
```

---

# Hook Rules

## Good Hooks
- emotionally provocative
- curiosity-based
- contradiction-based

## Examples
- “Emotionally safe men are different.”
- “The people who love hardest often fear intimacy.”
- “Confidence is quieter than people think.”

---

# Script Rules

## Sentence Style
- short
- emotionally dense
- conversational
- cinematic

---

# Example Prompt

```text
Generate a 40-second faceless YouTube Shorts script.

Topic:
What makes a man emotionally safe

Requirements:
- cinematic
- emotionally intelligent
- calm masculine energy
- high retention
- no cringe
```

---

# Example JSON Output

```json
{
  "hook": "...",
  "body": "...",
  "ending": "...",
  "cta": "..."
}
```

---

# Quality Validation

## Reject if:
- weak hook
- repetitive
- low emotional intensity
- generic advice
- too long

---

# Retention Optimization

## Techniques
- open loops
- emotional escalation
- pacing changes
- pauses
- contrast statements

---

# Example Python

```python
from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-5",
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ]
)

print(response.choices[0].message.content)
```

---

# Future Improvements

## Planned
- multi-agent script review
- emotional scoring
- retention prediction
- automated A/B hook generation