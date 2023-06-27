def assess_mental_disorder():
    print('''
\033[1;35m    _______     _______     _______     _______   \033[0m
\033[1;35m  //       \\ //       \\ //       \\ //       \\ \033[0m
\033[1;35m //         \V/         \V/         \V/         \\ \033[0m
\033[1;35m(|   \033[1;33mD   0  C   B   0   T \033[1;35m|) \033[0m
\033[1;35m \\         /|\         /|\         /|\         / \033[0m
\033[1;35m  \\_______// \\_______// \\_______// \\_______//  \033[0m
\033[1;32m
             ___
            |   |
          @ |  o|  @
            |   |
          /   _  \\
         /  ( )   \\
        / _/ | \_  \\
       / / \|/ \|\ \\
       \ \_/| |\_/ /
        \/   \/

\033[0m
''')
    
    print("Please answer the following questions with 'yes' or 'no':")
    
    depression_questions = [
        "Do you often feel sad or down?",
        "Have you lost interest or pleasure in activities you once enjoyed?",
        "Do you have trouble sleeping or experience changes in your sleep patterns?",
        "Do you feel tired or lack energy most days?",
        "Do you have trouble concentrating or making decisions?",
        "Have you experienced changes in appetite or weight?"
    ]
    
    gad_questions = [
        "Do you often feel worried or anxious?",
        "Do you find it difficult to control your worrying thoughts?",
        "Do you feel restless or on edge?",
        "Do you experience muscle tension or physical discomfort due to anxiety?",
        "Do you have difficulty falling asleep, staying asleep, or have restless, unsatisfying sleep?",
        "Do you have trouble concentrating or your mind going blank?"
    ]
    
    panic_disorder_questions = [
        "Do you experience sudden and repeated attacks of fear or discomfort?",
        "During these attacks, do you have symptoms such as a pounding heart, sweating, or trembling?",
        "Do you often worry about having another panic attack?",
        "Do you avoid certain situations or places because you're afraid of having a panic attack?"
    ]
    
    sad_questions = [
        "Do you feel intensely anxious or self-conscious in social situations?",
        "Do you avoid social situations or feel a strong urge to leave when you're in them?",
        "Do you worry excessively about embarrassing yourself or being judged by others?",
        "Do you often experience physical symptoms like blushing, sweating, or trembling in social situations?"
    ]
    
    depression_score = 0
    gad_score = 0
    panic_disorder_score = 0
    sad_score = 0
    
    for question in depression_questions:
        answer = input(question)
        if answer.lower() == "yes":
            depression_score += 1
    
    for question in gad_questions:
        answer = input(question)
        if answer.lower() == "yes":
            gad_score += 1
    
    for question in panic_disorder_questions:
        answer = input(question)
        if answer.lower() == "yes":
            panic_disorder_score += 1
    
    for question in sad_questions:
        answer = input(question)
        if answer.lower() == "yes":
            sad_score += 1
    
    print("\nAssessment Results:")
    print("Depression score:", depression_score)
    print("Generalized Anxiety Disorder (GAD) score:", gad_score)
    print("Panic Disorder score:", panic_disorder_score)
    print("Social Anxiety Disorder (SAD) score:", sad_score)
    
    if depression_score >= 3:
        print("You may have symptoms of depression. Please consult with a healthcare professional.")
    
    if gad_score >= 3:
        print("You may have symptoms of Generalized Anxiety Disorder (GAD). Please consult with a healthcare professional.")
    
    if panic_disorder_score >= 2:
        print("You may have symptoms of Panic Disorder. Please consult with a healthcare professional.")
    
    if sad_score >= 2:
        print("You may have symptoms of Social Anxiety Disorder (SAD). Please consult with a healthcare professional.")

# Run the assessment
assess_mental_disorder()
