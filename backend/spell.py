import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter

# ===============================================================================
# SPELL CORRECTION MODULE (Peter Norvig's Algorithm)
# ===============================================================================

def load_dictionary(dict_path):
    """
    Load word frequency dictionary from a text file.
    
    Args:
        dict_path (str): Path to the dictionary text file
        
    Returns:
        Counter: Word frequency counter
    """
    try:
        with open(dict_path, 'r', encoding='utf-8') as f:
            text = f.read()
            word_list = re.findall(r'\w+', text.lower())
            return Counter(word_list)
    except FileNotFoundError:
        print(f"⚠️  Warning: Dictionary file not found at {dict_path}")
        print("Using empty dictionary. Spell correction may not work properly.")
        return Counter()


def get_word_probability(word, word_freq_dict):
    """Calculate probability of a word based on frequency."""
    total = sum(word_freq_dict.values())
    if total == 0:
        return 0
    return word_freq_dict.get(word, 0) / total


def get_edits_distance_1(word):
    """Generate all words that are one edit away from the input word."""
    letters = 'abcdefghijklmnopqrstuvwxyz'
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [L + R[1:] for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces = [L + c + R[1:] for L, R in splits if R for c in letters]
    inserts = [L + c + R for L, R in splits for c in letters]
    return set(deletes + transposes + replaces + inserts)


def get_edits_distance_2(word):
    """Generate all words that are two edits away from the input word."""
    return (e2 for e1 in get_edits_distance_1(word) for e2 in get_edits_distance_1(e1))


def get_known_words(word_list, word_freq_dict):
    """Return the subset of words that appear in the dictionary."""
    return set(w for w in word_list if w in word_freq_dict)


def get_candidates(word, word_freq_dict):
    """Generate possible spelling corrections for a word."""
    return (get_known_words([word], word_freq_dict) or 
            get_known_words(get_edits_distance_1(word), word_freq_dict) or 
            get_known_words(get_edits_distance_2(word), word_freq_dict) or 
            [word])


def correct_word(word, word_freq_dict):
    """Return the most likely spelling correction for a word."""
    candidates = get_candidates(word, word_freq_dict)
    return max(candidates, key=lambda w: get_word_probability(w, word_freq_dict))


def extract_words(text):
    """Extract all words from text."""
    return re.findall(r'\w+', text.lower())


def correct_text(text, word_freq_dict):
    """
    Correct spelling mistakes in the entire text.
    
    Args:
        text (str): Input text to correct
        word_freq_dict (Counter): Word frequency dictionary
        
    Returns:
        tuple: (original_words, corrected_words, corrected_text)
    """
    original_words = extract_words(text)
    corrected_words = [correct_word(w, word_freq_dict) for w in original_words]
    corrected_text = ' '.join(corrected_words)
    return original_words, corrected_words, corrected_text


# ===============================================================================
# DATA ANALYSIS MODULE
# ===============================================================================

def analyze_spelling(original_words, corrected_words):
    """
    Analyze spelling mistakes and calculate statistics.
    
    Args:
        original_words (list): Original words from input
        corrected_words (list): Corrected words
        
    Returns:
        dict: Statistics including total words, mistakes, and percentage
    """
    total_words = len(original_words)
    mistakes = sum(1 for o, c in zip(original_words, corrected_words) if o != c)
    mistake_percentage = (mistakes / total_words * 100) if total_words > 0 else 0
    
    return {
        'total_words': total_words,
        'mistakes': mistakes,
        'mistake_percentage': mistake_percentage
    }


def determine_level_and_feedback(mistake_percentage):
    """
    Determine English proficiency level and provide feedback.
    
    Args:
        mistake_percentage (float): Percentage of spelling mistakes
        
    Returns:
        tuple: (level, feedback)
    """
    if mistake_percentage < 5:
        return "Advanced", "Excellent English! You're almost perfect."
    elif mistake_percentage >= 95:
        return "Very Poor", "Focus on basic grammar rules, spelling, and sentence structure."
    elif mistake_percentage > 40:
        level = "Beginner"
        feedback = "Your grammar needs significant improvement. Start from basics daily."
    else:
        level = "Needs Improvement"
        if mistake_percentage < 10:
            feedback = "Minor mistakes. Review tense and subject-verb agreement."
        elif mistake_percentage < 15:
            feedback = "You're doing well! Focus on spelling and grammar basics."
        elif mistake_percentage < 20:
            feedback = "Practice more with grammar exercises and proofreading."
        elif mistake_percentage < 25:
            feedback = "Work on prepositions, punctuation, and spelling errors."
        elif mistake_percentage < 30:
            feedback = "Revise tenses, plurals, and article usage regularly."
        elif mistake_percentage < 35:
            feedback = "Improve vocabulary and sentence structure with daily practice."
        else:
            feedback = "Work harder on subject-verb agreement and sentence flow."
    
    return level, feedback


# ===============================================================================
# DATA STORAGE MODULE
# ===============================================================================

def load_or_create_master_csv(master_path):
    """
    Load existing master CSV or create a new one.
    
    Args:
        master_path (str): Path to the master CSV file
        
    Returns:
        DataFrame: Master dataframe
    """
    if os.path.exists(master_path):
        return pd.read_csv(master_path)
    else:
        columns = [
            "Name", "Age", "Study", "Graduated", "Occupation", "Hobbies",
            "Goal", "Self_Intro", "Original_Input", "Corrected_Input",
            "Total_Words", "Mistakes", "Mistake_Percentage", "Level", "Feedback"
        ]
        return pd.DataFrame(columns=columns)


def save_to_master_csv(df, master_path):
    """
    Save dataframe to master CSV file.
    
    Args:
        df (DataFrame): Dataframe to save
        master_path (str): Path to save the CSV
    """
    df.to_csv(master_path, index=False)
    print(f"\n✅ Data saved to {master_path}")


def append_entry_to_master(entry_dict, master_path):
    """
    Append a single entry to the master CSV.
    
    Args:
        entry_dict (dict): Dictionary containing entry data
        master_path (str): Path to the master CSV file
        
    Returns:
        DataFrame: Updated master dataframe
    """
    df_master = load_or_create_master_csv(master_path)
    df_new = pd.DataFrame([entry_dict])
    df_master = pd.concat([df_master, df_new], ignore_index=True)
    save_to_master_csv(df_master, master_path)
    return df_master


# ===============================================================================
# USER INPUT MODULE
# ===============================================================================

def collect_user_details():
    """
    Collect user personal details through interactive prompts.
    
    Returns:
        dict: User details or None if user exits
    """
    print("\n" + "="*60)
    print("📋 PERSONAL DETAILS COLLECTION")
    print("="*60)
    
    name = input("👤 Name: ").strip()
    if name.lower() == 'exit':
        return None
    
    age = input("🎂 Age: ").strip()
    study = input("🎓 What are you studying (e.g., B.E, B.Tech, M.Sc, etc.): ").strip()
    is_graduate = input("🎓 Have you graduated? (yes/no): ").strip().lower()
    
    user_data = {
        'name': name,
        'age': age,
        'study': study,
        'graduated': is_graduate,
        'occupation': None,
        'hobbies': None,
        'goal': None,
        'self_intro': None
    }
    
    if is_graduate == "yes":
        user_data['occupation'] = input("💼 Current occupation: ").strip()
        user_data['hobbies'] = input("🎯 Hobbies: ").strip()
        user_data['goal'] = input("🎯 Future goal: ").strip()
        user_data['self_intro'] = input("📝 Self-intro (50 words): ").strip()
        print("\n✅ Thanks for sharing!\n")
    
    return user_data


def collect_text_for_analysis():
    """
    Collect text from user for spelling analysis.
    
    Returns:
        str: User input text
    """
    print("\n" + "="*60)
    print("📝 TEXT ANALYSIS")
    print("="*60)
    text = input("Enter your English sentence or paragraph to analyze:\n> ")
    return text


# ===============================================================================
# VISUALIZATION MODULE
# ===============================================================================

def plot_single_run_pie_chart(total_words, mistakes):
    """
    Create pie chart showing correct vs incorrect words for a single run.
    
    Args:
        total_words (int): Total number of words
        mistakes (int): Number of mistakes
    """
    correct = total_words - mistakes
    
    plt.figure(figsize=(8, 6))
    plt.pie([correct, mistakes],
            labels=['Correct', 'Mistakes'],
            autopct='%1.1f%%',
            startangle=140,
            colors=['#66b3ff', '#ff6666'],
            explode=(0.05, 0.05))
    plt.title('📊 Spelling Accuracy (Current Session)', fontsize=14, fontweight='bold')
    plt.axis('equal')
    plt.tight_layout()
    plt.show()


def plot_progress_over_time(master_path):
    """
    Plot mistake percentage progress over time for all users.
    
    Args:
        master_path (str): Path to the master CSV file
    """
    df_master = load_or_create_master_csv(master_path)
    
    if df_master.empty:
        print("⚠️  No data available for plotting.")
        return
    
    # Add session numbers for each user
    df_master['Session'] = df_master.groupby("Name").cumcount() + 1
    
    plt.figure(figsize=(12, 7))
    sns.lineplot(data=df_master, x="Session", y="Mistake_Percentage", 
                 hue="Name", marker='o', linewidth=2.5, markersize=8)
    
    plt.title("📈 Spelling Mistake Percentage Over Time by User", 
              fontsize=14, fontweight='bold')
    plt.xlabel("Session Number", fontsize=12)
    plt.ylabel("Mistake Percentage (%)", fontsize=12)
    plt.legend(title="User Name", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def display_results(stats, level, feedback, original_text, corrected_text):
    """
    Display analysis results to the user.
    
    Args:
        stats (dict): Statistics dictionary
        level (str): Proficiency level
        feedback (str): Feedback message
        original_text (str): Original input text
        corrected_text (str): Corrected text
    """
    print("\n" + "="*60)
    print("📊 ANALYSIS RESULTS")
    print("="*60)
    print(f"📝 Total Words: {stats['total_words']}")
    print(f"❌ Mistakes: {stats['mistakes']}")
    print(f"📉 Mistake Percentage: {stats['mistake_percentage']:.2f}%")
    print(f"🎯 Level: {level}")
    print(f"💡 Feedback: {feedback}")
    print("\n" + "-"*60)
    print("📄 ORIGINAL TEXT:")
    print(original_text)
    print("\n" + "-"*60)
    print("✅ CORRECTED TEXT:")
    print(corrected_text)
    print("="*60 + "\n")


# ===============================================================================
# MAIN APPLICATION
# ===============================================================================

def run_spelling_analyzer(dict_path=r"C:\Users\thanu\OneDrive\Desktop\assault\spelling checker\backend\big.txt", 
                         master_path="master.csv"):
    """
    Main function to run the spelling analyzer application.
    
    Args:
        dict_path (str): Path to the dictionary file
        master_path (str): Path to the master CSV file
    """
    print("\n" + "="*60)
    print("🔤 SPELLING ANALYZER APPLICATION")
    print("="*60)
    
    # Load dictionary
    print("📚 Loading dictionary...")
    word_freq_dict = load_dictionary(dict_path)
    
    if not word_freq_dict:
        print("❌ Cannot proceed without a valid dictionary. Exiting...")
        return
    
    print(f"✅ Dictionary loaded with {len(word_freq_dict)} unique words.\n")
    
    # Collect user details
    user_data = collect_user_details()
    if user_data is None:
        print("👋 Exiting application...")
        return
    
    # Collect text for analysis
    user_text = collect_text_for_analysis()
    
    # Perform spelling correction
    print("\n🔍 Analyzing text...")
    original_words, corrected_words, corrected_text = correct_text(user_text, word_freq_dict)
    
    # Analyze statistics
    stats = analyze_spelling(original_words, corrected_words)
    level, feedback = determine_level_and_feedback(stats['mistake_percentage'])
    
    # Display results
    display_results(stats, level, feedback, user_text, corrected_text)
    
    # Prepare entry for storage
    entry = {
        "Name": user_data['name'],
        "Age": user_data['age'],
        "Study": user_data['study'],
        "Graduated": user_data['graduated'],
        "Occupation": user_data['occupation'],
        "Hobbies": user_data['hobbies'],
        "Goal": user_data['goal'],
        "Self_Intro": user_data['self_intro'],
        "Original_Input": user_text,
        "Corrected_Input": corrected_text,
        "Total_Words": stats['total_words'],
        "Mistakes": stats['mistakes'],
        "Mistake_Percentage": stats['mistake_percentage'],
        "Level": level,
        "Feedback": feedback
    }
    
    # Save to master CSV
    print("💾 Saving data to master CSV...")
    df_master = append_entry_to_master(entry, master_path)
    
    print("\n📁 Master dataset summary:")
    print(f"   Total entries: {len(df_master)}")
    print(f"   Unique users: {df_master['Name'].nunique()}")
    
    # Visualizations
    print("\n📊 Generating visualizations...\n")
    plot_single_run_pie_chart(stats['total_words'], stats['mistakes'])
    plot_progress_over_time(master_path)
    
    print("\n✅ Analysis complete! Thank you for using Spelling Analyzer.\n")


# ===============================================================================
# ENTRY POINT
# ===============================================================================

if __name__ == "__main__":
    # You can customize these paths
    DICTIONARY_PATH = r"C:\Users\thanu\OneDrive\Dokumen\big.txt"
    MASTER_CSV_PATH = "master.csv"
    
    run_spelling_analyzer(DICTIONARY_PATH, MASTER_CSV_PATH)