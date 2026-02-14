from moments import MomentDetector, MomentType

def test_moment_detection():
    detector = MomentDetector(window_size=15)
    
    print("=== Testing HYPE detection ===")
    detector.clear()
    hype_messages = [
        "LETS GOO",
        "poggers",
        "that was insane",
        "POGU",
        "WE WIN",
        "actual god gamer",
        "clutch play",
    ]
    for msg in hype_messages:
        detector.add_message(msg)
    result = detector.detect()
    print(f"Messages: {hype_messages}")
    print(f"Detected: {result.value} (expected: hype)")
    print(f"Fallback: {detector.get_fallback(result)}")
    print()

    print("=== Testing SADGE detection ===")
    detector.clear()
    sad_messages = [
        "rip",
        "Sadge",
        "unlucky man",
        "pain",
        "F in chat",
        "he threw",
        "not like this",
    ]
    for msg in sad_messages:
        detector.add_message(msg)
    result = detector.detect()
    print(f"Messages: {sad_messages}")
    print(f"Detected: {result.value} (expected: sadge)")
    print(f"Fallback: {detector.get_fallback(result)}")
    print()

    print("=== Testing EMOTE_SPAM detection ===")
    detector.clear()
    emote_messages = [
        "KEKW",
        "LULW LULW",
        "OMEGALUL",
        "PepeLaugh",
        "KEKW KEKW KEKW",
        "catJAM",
        "LULW",
    ]
    for msg in emote_messages:
        detector.add_message(msg)
    result = detector.detect()
    print(f"Messages: {emote_messages}")
    print(f"Detected: {result.value} (expected: emote_spam)")
    print(f"Fallback: {detector.get_fallback(result)}")
    print()

    print("=== Testing QUESTION detection ===")
    detector.clear()
    question_messages = [
        "what game is this?",
        "when did he start streaming?",
        "is this ranked?",
        "how long has he been live?",
        "anyone know what song this is?",
        "yo chat what happened?",
    ]
    for msg in question_messages:
        detector.add_message(msg)
    result = detector.detect()
    print(f"Messages: {question_messages}")
    print(f"Detected: {result.value} (expected: question)")
    print(f"Fallback: {detector.get_fallback(result)}")
    print()

    print("=== Testing GREETING detection ===")
    detector.clear()
    greeting_messages = [
        "hi chat",
        "hello everyone",
        "hey hey",
        "yo whats up",
        "hiii",
        "just got here",
    ]
    for msg in greeting_messages:
        detector.add_message(msg)
    result = detector.detect()
    print(f"Messages: {greeting_messages}")
    print(f"Detected: {result.value} (expected: greeting)")
    print(f"Fallback: {detector.get_fallback(result)}")
    print()

    print("=== Testing NEUTRAL detection ===")
    detector.clear()
    neutral_messages = [
        "yeah that makes sense",
        "i think so too",
        "fair enough",
        "lol true",
        "nice one",
        "thats cool",
        "same honestly",
    ]
    for msg in neutral_messages:
        detector.add_message(msg)
    result = detector.detect()
    print(f"Messages: {neutral_messages}")
    print(f"Detected: {result.value} (expected: neutral)")
    print(f"Fallback: {detector.get_fallback(result)}")
    print()

    print("=== Testing mixed chat (should stay neutral) ===")
    detector.clear()
    mixed_messages = [
        "that was a good play",
        "KEKW",
        "wait what happened",
        "nice",
        "true lol",
        "i missed it",
        "oh damn",
        "classic",
    ]
    for msg in mixed_messages:
        detector.add_message(msg)
    result = detector.detect()
    print(f"Messages: {mixed_messages}")
    print(f"Detected: {result.value} (expected: neutral)")
    print()

    print("=== Testing gradual moment shift ===")
    detector.clear()
    print("Starting neutral...")
    for msg in ["nice stream", "loving this", "chill vibes"]:
        detector.add_message(msg)
    print(f"  Current: {detector.detect().value}")
    
    print("Hype building...")
    for msg in ["oh damn", "WAIT", "LETS GO", "POGGERS", "HE DID IT"]:
        detector.add_message(msg)
    print(f"  Current: {detector.detect().value}")
    
    print("Hype continuing...")
    for msg in ["INSANE", "CLUTCH", "actual god"]:
        detector.add_message(msg)
    print(f"  Current: {detector.detect().value}")


if __name__ == "__main__":
    test_moment_detection()