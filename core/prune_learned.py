import re
import argparse
from datetime import datetime
import markovify

def prune_learned_log(input_file, output_file, auto_overwrite=False, generate_mass=0, output_messages=None):
    pattern = re.compile(r"\[(.*?)\] (.+)")
    multi_word_lines = []
    single_word_messages = []
    seen_messages = set()

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                match = pattern.match(line.strip())
                if match:
                    _, message = match.groups()
                    if "@" in message and re.search(r'@\w+', message):
                        continue  # skip messages with @usernames

                    normalized = message.strip().lower()
                    if normalized in seen_messages:
                        continue
                    seen_messages.add(normalized)

                    if len(message.split()) >= 2:
                        multi_word_lines.append(message.strip())
                    else:
                        single_word_messages.append(message.strip())
    except FileNotFoundError:
        print(f"[ERROR] Could not find {input_file}")
        return

    # group up single worded messages
    grouped_lines = []
    for i in range(0, len(single_word_messages), 5):
        group = " ".join(single_word_messages[i:i+5])
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        grouped_lines.append(f"[{timestamp}] {group}")

    output_lines = [f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {line}" for line in multi_word_lines] + grouped_lines

    target_file = input_file if auto_overwrite else output_file
    with open(target_file, "w", encoding="utf-8") as f:
        for line in output_lines:
            f.write(line + "\n")

    print(f"[PRUNE DONE] Wrote {len(output_lines)} entries to {target_file}")
    print(f"[INFO] {len(multi_word_lines)} long messages kept, {len(grouped_lines)} new grouped lines.")

    # build model
    all_sentences = multi_word_lines + [g.split("] ")[1] for g in grouped_lines]
    model = markovify.NewlineText("\n".join(all_sentences), state_size=1)

    print("\n[MARKOV TEST] Generating sample messages...\n")
    for _ in range(5):
        result = model.make_short_sentence(200)
        print(f"→ {result}" if result else "→ (No sentence generated)")

    # mass generation file 
    if generate_mass > 0 and output_messages:
        generated = set()
        tries = 0
        while len(generated) < generate_mass and tries < generate_mass * 5:
            sentence = model.make_short_sentence(300)
            if sentence:
                norm = sentence.strip().lower()
                if norm not in generated:
                    generated.add(sentence.strip())
            tries += 1

        with open(output_messages, "w", encoding="utf-8") as f:
            for s in generated:
                f.write(s + "\n")
        print(f"\n[MASS GEN] Wrote {len(generated)} messages to {output_messages}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prune and restructure learned.log for LilVikBot")
    parser.add_argument("-i", "--input", default="learned.log", help="Input learned log file")
    parser.add_argument("-o", "--output", default="learned_reshaped.log", help="Output file (unless --overwrite is used)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the input file directly")
    parser.add_argument("--generate-mass", type=int, default=0, help="Number of mass-generated messages to output")
    parser.add_argument("--output-messages", default=None, help="Path to save mass-generated messages")
    args = parser.parse_args()

    prune_learned_log(
        input_file=args.input,
        output_file=args.output,
        auto_overwrite=args.overwrite,
        generate_mass=args.generate_mass,
        output_messages=args.output_messages
    )
