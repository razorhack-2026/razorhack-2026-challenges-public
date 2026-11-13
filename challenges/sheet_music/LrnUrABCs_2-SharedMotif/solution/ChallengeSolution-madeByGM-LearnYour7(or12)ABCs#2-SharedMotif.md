## ChallengeName  
Learn Your 7 (or 12) ABCs #2 - Shared Motif  

**Category:**    Steganography / Sheet Music  
**Difficulty:**  training  
**Author:**      "Mort"  

### ChallengeDescription_Themed_ViewableByParticipant  
Heard by ear and transcribed to sheet music, a security officer had a hunch that note names present in the sheet music covertly sound the song of the crew's flag. Can you verify their hunch?  

### FilesProvidedToParticipant  
* dist/LrnUrABCs_2-SharedMotif.pdf  
* dist/LrnUrABCs_2-SharedMotif.mid  

### Flags that participant can submit  
* flag{bagdad}  
* flag{BAGDAD}  
* FLAG{bagdad}  
* FLAG{BAGDAD}  

## Solution
1) Noticeable quirk about the data: Listening to the recording makes it seem like each measure is just a variation of the same overall theme.  
2) Technique: Get name of each note within the first measure.  
3) Flag Recovery: The first 6 note names as a string is the flag.  

### Known Issues / Notes  
1) The 1st and 2nd measures provide the flag directly and easily, but the following measures can also give you the flag if you're an expert in interpreting chords (I am not, but Lilypond software allows easy transposition and easy creation of chords).  

