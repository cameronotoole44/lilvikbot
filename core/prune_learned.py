import re
import argparse
from datetime import datetime
import markovify

def prune_learned_log(input_file, output_file, auto_overwrite=False):
    pattern = re.compile(r"\[(.*?)\] (.+)")
    multi_word_lines = []
    single_word_messages = []

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                match = pattern.match(line.strip())
                if match:
                    _, message = match.groups()
                    if len(message.split()) >= 2:
                        multi_word_lines.append(message.strip())
                    else:
                        single_word_messages.append(message.strip())
    except FileNotFoundError:
        print(f"[ERROR] Could not find {input_file}")
        return

    # groups 1-word messages into lines of 5
    grouped_lines = []
    for i in range(0, len(single_word_messages), 5):
        group = " ".join(single_word_messages[i:i+5])
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        grouped_lines.append(f"[{timestamp}] {group}")

    # final out put lines
    output_lines = [f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {line}" for line in multi_word_lines] + grouped_lines

    target_file = input_file if auto_overwrite else output_file
    with open(target_file, "w", encoding="utf-8") as f:
        for line in output_lines:
            f.write(line + "\n")

    print(f"[PRUNE DONE] Wrote {len(output_lines)} entries to {target_file}")
    print(f"[INFO] {len(multi_word_lines)} long messages kept, {len(grouped_lines)} new grouped lines.")

    # build and test new model
    print("\n[MARKOV TEST] Generating sample messages...\n")
    model = markovify.NewlineText("\n".join(multi_word_lines + [g.split("] ")[1] for g in grouped_lines]), state_size=1)

    for _ in range(5):
        result = model.make_short_sentence(200)
        print(f"→ {result}" if result else "→ (No sentence generated)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prune and restructure learned.log for LilVikBot")
    parser.add_argument("-i", "--input", default="learned.log", help="Input learned log file")
    parser.add_argument("-o", "--output", default="learned_reshaped.log", help="Output file (unless --overwrite is used)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the input file directly")

    args = parser.parse_args()
    prune_learned_log(args.input, args.output, auto_overwrite=args.overwrite)
