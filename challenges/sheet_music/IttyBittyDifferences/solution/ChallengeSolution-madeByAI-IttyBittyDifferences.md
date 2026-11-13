## ChallengeName  
Itty Bitty Differences  

**Difficulty:**  medium  
**Category:**    Steganography / Sheet Music  
**Author:**      "Mort"  

### ChallengeDescription_Themed_ViewableByParticipant  
Heard by ear and transcribed to sheet music, a security officer noticed a theme that was repeated with slight variations during each repeat, thinking that the composer may have somehow hidden a message in the thematic differences. Can you verify their hunch?  

### FilesProvidedToParticipant  
* dist/IttyBittyDifferences.ly  
* dist/IttyBittyDifferences.pdf  
* dist/IttyBittyDifferences.mid  

### Flags that participant can submit  
* flag{b1tw153_m0d1f1c4t10n5_f40m_th3_phr453}  
* flag{B1TW153_M0D1F1C4T10N5_F40M_TH3_PHR453}  
* FLAG{b1tw153_m0d1f1c4t10n5_f40m_th3_phr453}  
* FLAG{B1TW153_M0D1F1C4T10N5_F40M_TH3_PHR453}  

## Solution
1) noticeable quirks about the data: Every measure sounds nearly identical.  
2) key insight: Realize that the very first (0th) measure sounds the most sane, so treat it as a reference measure.  
3) Flag recovery: Does currMeasure's noteName exactly match 0thMeasure's noteName? If different, then assign currPitch to have bitValue1, else assign bitValue0. Combine all 1s and 0s into 8-bit values into very long bitstrin. Turn into ASCII chars, which is the flag.  

### Known Issues / Notes  
No issues nor notes about this challenge.  




The challenge title "Itty Bitty Differences" hints at bitwise differences.


## Baseline Template (Measure #0):  
Measure #0 contains the 8 reference notes, each of which is "natural":  
`c'  e'  b'  a'  g'  f'  e'  c'`

## Bitwise Encoding Rule:  
Each measure from #1 to #43 contains 8 quarter notes, the set of 8 notes corresponding to an 8-bit binary character:  

**Unmodified Note** (matches Measure #0): **0**  
**Modified Note** (flattened f or sharpened s): **1**  

## Bit Order:  
Bits are ordered sequentially from left to right (MSB first, bit 7 to bit 0):  
<!-- $$\text{ASCII Value} = \sum_{j=0}^{7} b_j \cdot 2^{7-j}$$   -->
**ASCII Value** = Sum_{j=0}^7 ( b_j * 2^{7-j} )  


## Step-by-Step Solution Breakdown  

Measure **#1:**  
* Notes: `c' ef' bf' a' g' fs' ef' c'`  
* Baseline Comparison:  
  * c' = c' $\rightarrow 0$  
  * ef' $\neq$ e' $\rightarrow 1$  
  * bf' $\neq$ b' $\rightarrow 1$  
  * a' = a' $\rightarrow 0$  
  * g' = g' $\rightarrow 0$  
  * fs' $\neq$ f' $\rightarrow 1$  
  * ef' $\neq$ e' $\rightarrow 1$  
  * c' = c' $\rightarrow 0$  
* Binary: 01100110 = $102_{10}$ = `f`  

...  

Measure **#5:**  
* Notes: `c' ef' bf' af' gf' f' ef' cs'`  
* Bit Diff: 01111011 = $123_{10}$ = `{`  

...  

Measure **#13:**  
* Notes: `c' ef' b' af' gf' fs' ef' cs'`  
* Bit Diff: 01011111 = $95_{10}$ = `_`  

...  

Measure **#43:**  
* Notes: `c' ef' bf' af' gf' fs' e' cs'`  
* Bit Diff: 01111101 = $125_{10}$ = `}`  


