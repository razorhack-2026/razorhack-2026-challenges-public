# CTF Challenge Solution: Expression of Regularity  

## Challenge Overview  
**Challenge Name:** Expression of Regularity  
**Creator:**    Mort (StevieoXOR)  
**Difficulty:** hard  
**Category:**   Stego (Steganography)  

**ChallengeDescription_Themed_ViewableByParticipant:**  
An informational explanatory document was intercepted, but contained a few sentences that didn't quite make sense, so a security officer decided to push it up the chain for further analysis.  

FilesProvidedToParticipant  
- dist/RegularFile.odt  
- dist/RegularFile.txt  

**Flags:**  
- flag{gapsbetweenchars}  
- flag{gapsbetweenCharss}  
- flag{gapsbetweenChars}  
- flag{gaps_between_chars}  
- flag{gaps_between_Chars}  
- flag{GapsBetweenChars}  
- flag{gapsBetweenChars}  

**Tools required to solve challenge:**  
* Knowledge of Regular Expressions, mainly that `(.*)` placed between two characters (e.g., `f(.*)l`) will allow ANY characters in ANY quantity to exist between those two characters, while still only matching if those two surrounding characters exist.  
* A RegEx parser that can take essay-length strings of input and find at least one match. Tested options that worked successfully:  
  * LibreOffice Writer's `Find & Replace` tool (ensure the "Regular Expressions" option is selected!)  
  * https://regex101.com/  

**Solve Technique:**  
1. Participant doesn't want to read too much, so they CTRL+F for "flag" (case-insensitive).  
2. They don't find anything, but they think "what if I looked for 'flag' with an arbitrary-length gap in between each character in the 'flag' string?".  
3. That leads them to creating any one of the following RegEx strings:  
  * "f(.*)l(.*)a(.*)g"  
  * "F(.*)L(.*)A(.*)G"  
  * "[fF](.*)[lL](.*)[aA](.*)[gG]"  
  * "[fF](.*?)[lL](.*?)[aA](.*?)[gG]"  
4. Participant uses the regex on the provided `.odt` or `.txt` file, and finds two matches. One match occurs near the start of a sentence, and the next match is near the start of the following adjacent sentence.  
5. Sentences of interest:  
  * "Fifty bloodbath eggs aged maps upon tsar absorbed pitch awakened meets knee scratches carriers assess."  
  * "Staff solve bad bugs logic lags updates probe them until two are freed since MCUs that fail grow useless."  
6. Participant notices that the two sentences are weird, and contextually out-of-place given the rest of the essay.  
7. Participant notices that there are exactly 4 characters (including spaces) between each matched character in the chars in the string "flag".  
8. Participant decides to extend past those "flag" characters, highlighting/bolding every 5th character that occurs after the f l a g characters, in the hopes that it spells out something.  
9. Participant combines the highlighted/bolded characters (from either of the two sentences, but not both) into a single string, resulting in the string (ending at the end of each sentence) "flaggapsbetweenchars".  
10. Participant assumes flag is "flag{gapsbetweenchars}" (if they chose the first sentence) or "flag{gapsbetweenCharss}" (if they chose the second sentence).  
11. Participant hopefully realizes that the latter flag does not need the very last "s" to make sense, shortening the flag to just "flag{gapsbetweenchars}".  

