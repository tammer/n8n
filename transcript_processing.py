import json


def process_transcript(sentences):
    """
    Takes a list of sentence dictionaries and returns JSON-serialisable data
    containing a human‑readable transcript.

    Expected input format (per item in `sentences`):
      {
        "id": int,
        "transcript": str,
        "timestamp": str,  # ISO-8601, optional for this function
        "speaker": str
      }

    Return value example:
      {
        "transcript": "Speaker A: Hello\\nSpeaker B: Hi there"
      }
    """
    if not sentences:
        return {"transcript": ""}

    lines = []
    current_speaker = None
    current_chunks = []

    for item in sentences:
        speaker = item.get("speaker") or "Unknown speaker"
        text = item.get("transcript", "")

        # Skip completely empty texts
        if not text:
            continue

        # If this is the same speaker as the previous one, just accumulate text
        if speaker == current_speaker:
            current_chunks.append(text)
        else:
            # Flush previous speaker, if any
            if current_speaker is not None:
                joined = " ".join(current_chunks)
                lines.append(f"{current_speaker}: {joined}")

            # Start tracking new speaker
            current_speaker = speaker
            current_chunks = [text]

    # Flush the last speaker group
    if current_speaker is not None and current_chunks:
        joined = " ".join(current_chunks)
        lines.append(f"{current_speaker}: {joined}")

    human_readable = "\n".join(lines)
    return {"transcript": human_readable}


if __name__ == "__main__":
    # Example input data (Python structure equivalent to the original JSON)
    sentences = [
        {
            "id": 1,
            "transcript": "Thank",
            "timestamp": "2025-12-05T17:58:48.103000+00:00",
            "speaker": "Unknown speaker",
        },
        {
            "id": 2,
            "transcript": "Good.",
            "timestamp": "2025-12-05T17:59:46.609000+00:00",
            "speaker": "Unknown speaker",
        },
        {
            "id": 3,
            "transcript": "Hello.",
            "timestamp": "2025-12-05T18:00:16.663000+00:00",
            "speaker": "Unknown speaker",
        },
        {
            "id": 4,
            "transcript": "Hello.",
            "timestamp": "2025-12-05T18:00:18.045000+00:00",
            "speaker": "Elie Kasongo",
        },
        {
            "id": 5,
            "transcript": "I'm",
            "timestamp": "2025-12-05T18:00:19.947000+00:00",
            "speaker": "Elie Kasongo",
        },
        {
            "id": 6,
            "transcript": "very good, thanks.",
            "timestamp": "2025-12-05T18:00:20.108000+00:00",
            "speaker": "Tammer Kamel",
        },
        {
            "id": 7,
            "transcript": "How are you?",
            "timestamp": "2025-12-05T18:00:20.789000+00:00",
            "speaker": "Tammer Kamel",
        },
        {
            "id": 8,
            "transcript": "I'm very, very good.",
            "timestamp": "2025-12-05T18:00:21.209000+00:00",
            "speaker": "Elie Kasongo",
        },
    ]

    print(json.dumps(process_transcript(sentences), indent=4))