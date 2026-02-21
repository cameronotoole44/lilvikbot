import os
import re
import argparse
from datetime import datetime
from collections import Counter
import markovify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
DEFAULT_INPUT = os.path.join(DATA_DIR, "learned.log")
DEFAULT_OUTPUT = os.path.join(DATA_DIR, "learned_pruned.log")
DEFAULT_MASS_OUTPUT = os.path.join(DATA_DIR, "mass_posts.txt")
MIN_WORDS = 3
MAX_DUPLICATES = 2

def extract_message(line: str) -> str | None:
    match = re.match(r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] (.+)", line.strip())
    if match:
        return match.group(1).strip()
    return None

def normalize(text: str) -> str:
    # lowercase, remove extra spaces
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def is_quality_message(msg: str) -> bool:
    words = msg.split()
    
    if len(words) < MIN_WORDS:
        return False
    
    if msg.isupper() and len(words) < 5:
        return False
    
    unique_words = set(words)
    if len(unique_words) == 1:
        return False
    
    word_counts = Counter(words)
    most_common_count = word_counts.most_common(1)[0][1]
    if most_common_count > len(words) * 0.6:
        return False
    
    # has @mentions (should be filtered - double check)
    if re.search(r'@\w+', msg):
        return False
    
    return True


def prune_learned_log(input_file, output_file, auto_overwrite=False, generate_mass=0, output_messages=None, dry_run=False):
    
    if not os.path.exists(input_file):
        print(f"[ERROR] Could not find {input_file}")
        return
    
    messages = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            msg = extract_message(line)
            if msg:
                messages.append(msg)
    
    print(f"[INPUT] Read {len(messages)} messages from {input_file}")
    
    seen = Counter()
    kept = []
    removed_short = 0
    removed_quality = 0
    removed_duplicate = 0
    
    for msg in messages:
        norm = normalize(msg)
        
        if len(msg.split()) < MIN_WORDS:
            removed_short += 1
            continue
        
        if not is_quality_message(msg):
            removed_quality += 1
            continue
        
        # dupe check
        if seen[norm] >= MAX_DUPLICATES:
            removed_duplicate += 1
            continue
        
        seen[norm] += 1
        kept.append(msg)
    
    print(f"\n[STATS]")
    print(f"  Removed (too short): {removed_short}")
    print(f"  Removed (low quality): {removed_quality}")
    print(f"  Removed (duplicates): {removed_duplicate}")
    print(f"  Kept: {len(kept)}")
    print(f"  Reduction: {len(messages) - len(kept)} messages ({100 * (len(messages) - len(kept)) / len(messages):.1f}%)")
    
    if dry_run:
        print("\n[DRY RUN] No files modified")
    else:
        target_file = input_file if auto_overwrite else output_file
        with open(target_file, "w", encoding="utf-8") as f:
            for msg in kept:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {msg}\n")
        
        print(f"\n[DONE] Wrote {len(kept)} messages to {target_file}")
    
    # test it
    if kept:
        model = markovify.NewlineText("\n".join(kept), state_size=2)
        
        print("\n[MARKOV TEST] Generating sample messages (state_size=2):\n")
        for _ in range(10):
            result = model.make_short_sentence(200, tries=100)
            print(f"  {result}" if result else "  (No sentence generated)")
    
    # mass gen
    if generate_mass > 0 and output_messages and not dry_run:
        model = markovify.NewlineText("\n".join(kept), state_size=2)
        generated = set()
        tries = 0
        max_tries = generate_mass * 10
        
        while len(generated) < generate_mass and tries < max_tries:
            sentence = model.make_short_sentence(200, tries=100)
            if sentence and sentence not in generated:
                generated.add(sentence)
            tries += 1
        
        with open(output_messages, "w", encoding="utf-8") as f:
            for s in generated:
                f.write(s + "\n")
        
        print(f"\n[MASS GEN] Wrote {len(generated)} messages to {output_messages}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prune and deduplicate learned.log for LilVikBot")
    parser.add_argument("-i", "--input", default=DEFAULT_INPUT, help="Input learned log file")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT, help="Output file (unless --overwrite is used)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the input file directly")
    parser.add_argument("--dry-run", action="store_true", help="Show stats without modifying files")
    parser.add_argument("--generate-mass", type=int, default=0, help="Number of mass-generated messages to output")
    parser.add_argument("--output-messages", default=DEFAULT_MASS_OUTPUT, help="Path to save mass-generated messages")
    args = parser.parse_args()

    prune_learned_log(
        input_file=args.input,
        output_file=args.output,
        auto_overwrite=args.overwrite,
        generate_mass=args.generate_mass,
        output_messages=args.output_messages,
        dry_run=args.dry_run
    )
