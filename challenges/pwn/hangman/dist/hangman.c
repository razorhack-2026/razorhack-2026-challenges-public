#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <ctype.h>

struct Session {
    // In the future, there will be multiple dictionaries players can choose from.
    char player[0x20];
    char dict[0xFF];
    unsigned int lives;
};

int main() {
    struct Session sess;
 // MAKE SURE TO COMMENT THIS OUT BEFORE PUSHING TO PROD!!!
 // sess.dict_name = "test_dict.txt
    strcpy(sess.dict, "dictionary.txt");

    printf("Welcome to Hangman!\nEnter your name: ");

    srand(time(NULL));

    fgets(sess.player, 0x30, stdin);
    sess.player[strcspn(sess.player, "\n")] = '\0';
    sess.lives = 6;

    printf("\nWelcome %s!\n", sess.player);



    unsigned int t_line = rand() % 10000 + 1; // 1-indexed
    unsigned int c_line = 0;

    char word[0xFF] = {0};
    unsigned int word_len = 0;

    FILE* dict_file = fopen(sess.dict, "r");
    while (c_line < t_line && fgets(word, 0xFF, dict_file)) {
        c_line++;
    }

    word[strcspn(word, "\n")] = '\0';
    word_len = strlen(word);



    char seen[0xFF] = {0};
    unsigned int seen_len = 0;

    unsigned int lives = 3;
    while (1) {
        printf("\nGuess the word! You have %d lives left!\n", lives);

        unsigned int win = 1;
        for (unsigned int i = 0; i < word_len; i++) {
            if (strchr(seen, word[i]) != NULL) {
                printf("%c ", word[i]);
            } else {
                printf("_ ");
                win = 0;
            }
        }

        if (win) {
            printf("\n\nGreat job %s, you won!", sess.player);
            return 0;
        } else if (lives <= 0) {
            printf("\n\nDon't worry %s, you'll get it next time! The word was '%s'.", sess.player, word);
            return 0;
        }

        printf("\n\nEnter your guess: ");
        fflush(stdout);

        char guess[0xFF];
        unsigned int guess_len = 0;

        if(fgets(guess, 0xFF, stdin) == NULL) {
            printf("Failed to read input.");
            return 0;
        }
        guess[strcspn(guess, "\n")] = '\0';
        guess_len = strlen(guess);

        if (guess_len > 1)  { printf("You may only guess 1 character at a time!\n"); continue; }
        if (guess_len == 0) { printf("Please enter your guess!\n"); continue; }

        guess[0] = tolower(guess[0]);
        if (strchr(seen, guess[0]) != NULL) { printf("You already guessed that letter!\n"); continue; }

        if (strchr(word, guess[0]) == NULL) {
            lives--;
        }

        seen[seen_len] = guess[0];
        seen_len++;
    }
}


