# CTF Challenge Solution: Conditionally Visible  

## Challenge Overview  
**Challenge Name:** Conditionally Visible  
**Creator:**    Mort (StevieoXOR)  
**Difficulty:** medium  
**Category:**   Stego (Steganography)  

**ChallengeDescription_Themed_ViewableByParticipant:**  
A technical document that explains four different privacy-preserving techniques was intercepted, but the file contained an ever-so-slightly larger number of newlines than one might expect in a technical report, as if it were generated from LaTeX. A security officer begrudgingly decided to push it up the chain for further analysis, only catching it due to security protocols mandating statistical analysis. Is there any secret data being communicated in this file, or is it exactly as it seems?  

FilesProvidedToParticipant  
- dist/GuideTo_LossyAndNonlossy_PrivacyModels_T-K-L_Diff--Priv.md  

**Flags:**  
- `flag{K-Anonymity+L-+T-[1053n3zz_I5_B3tt3R_Th4|\|_D1ff3r3|\|t141_Pr1\/4[`/_sumTimes}`  
- `FLAG{K-Anonymity+L-+T-[1053n3zz_I5_B3tt3R_Th4|\|_D1ff3r3|\|t141_Pr1\/4[`/_sumTimes}`  

**Tools required to solve challenge:**  
* How to read data in from a file on Disk (or be able to copy and pipe that data)  
* Python's MyString.split("\n") function  
* How to read backwards from the end of each line of text  

**Solve Technique:**  
1. Participant opens `dist/GuideTo_LossyAndNonlossy_PrivacyModels_T-K-L_Diff--Priv.md`, then presses CTRL+A in the file and sees whitespace (tabs and spaces) at the end of each line.  
2. They don't find anything flag-related, but they think "what if these characters at the end of each line form the flag string?".  
3. That leads them to assuming UTF-8 encoding (likely implicitly rather than explicitly), meaning they assume 8 bits per char.  
4. Participant eventually notices that the whitespace isn't consistent; it's made up of both space characters and tab characters.  
5. Participant writes script (likely with LLM's help) to extract the last characters of each line of text read in from a file, stopping reading each line whenever encountering that line's first (from right-to-left though) non-whitespace character (e.g., a letter of the alphabet).  
6. Participant tries TAB=binaryValue0 & SPACE=binaryValue1, and/or TAB=binaryValue1 & SPACE=binaryValue0.  
7. Participant concatenates the bits discovered in each line, from the top line to the bottom line, into a single bitstring.  
8. Participant chunks the bitstring into 8-bit-wide (mutually exclusive) segments, and then decodes each 8-bit segment into a single character using something like `encodings.decode(MyBytestring, "utf-8")` (from the codecs library) or `chr(segmentWith8Bits)`.  
9. Participant discovers that the flag is ```"flag{K-Anonymity+L-+T-[1053n3zz_I5_B3tt3R_Th4|\|_D1ff3r3|\|t141_Pr1\/4[`/_sumTimes}"```.  



## How to build the challenge from scratch  

1) Ensure you have the following initialization files (and that they're located in the correct folders too!):  
* `solution/StegoLineEnding.py`  
* `dist/GuideTo_LossyAndNonlossy_PrivacyModels_T-K-L_Diff--Priv.md`  

2) Next, run the Python file in Windows Command Prompt via `py solution/StegoLineEnding.py`.  

3) After the Python file finishes its execution, the following files will have been created:  
* `solution/debug-encodedButVisibleStegotext.txt`  
  * Visibly encoded  
* `dist/GuideTo_LossyAndNonlossy_PrivacyModels_T-K-L_Diff--Priv.md`  
  * Invisibly encoded (using the same secret bits as the debug version)  

