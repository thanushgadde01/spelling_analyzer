"""cli.py - terminal version (replaces the interactive part of the old spell.py). Charts need matplotlib+seaborn."""
from spell import SpellChecker, determine_level_and_feedback
from storage import append_entry_to_master, load_or_create_master_csv


def main(master_path="master.csv"):
    checker = SpellChecker()
    name = input("Name (or 'exit'): ").strip()
    if name.lower() == "exit":
        return
    text = input("Enter your English text:\n> ")
    res = checker.check(text)
    level, feedback = determine_level_and_feedback(res.spelling_percentage, res.grammar_percentage)

    print(f"\nWords: {res.total_words} | Spelling: {res.spelling_mistakes} ({res.spelling_percentage:.1f}%)"
          f" | Grammar: {len(res.grammar)}\nLevel: {level} - {feedback}\n\nCorrected:\n{res.corrected}\n")
    for c in res.corrections:
        print(f"  {c.original} -> {c.suggestion}  ({c.confidence:.0%}, {'fixed' if c.applied else 'please review'})")
    for g in res.grammar:
        print(f"  [grammar] {g.message}")

    append_entry_to_master({
        "Name": name, "Original_Input": text, "Corrected_Input": res.corrected, "Total_Words": res.total_words,
        "Mistakes": res.spelling_mistakes, "Mistake_Percentage": res.spelling_percentage,
        "Grammar_Issues": len(res.grammar), "Level": level, "Feedback": feedback}, master_path)

    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError:
        return
    df = load_or_create_master_csv(master_path)
    df["Session"] = df.groupby("Name").cumcount() + 1
    sns.lineplot(data=df, x="Session", y="Mistake_Percentage", hue="Name", marker="o")
    plt.title("Spelling mistake % over time")
    plt.show()


if __name__ == "__main__":
    main()
