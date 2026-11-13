use wasm_bindgen::prelude::*;
use sha2::{Sha256, Digest};
use hex_literal::hex;

#[wasm_bindgen(module = "/helper.js")]
extern "C" {
    pub fn set(s: &str);
}

#[wasm_bindgen]
extern "C" {
    pub fn alert(s: &str);
}

fn print_flag() {
    let a: [u8; 28] = [101, 118, 101, 114, 121, 111, 110, 101, 32, 105, 115, 32, 97, 108, 119, 97, 121, 115, 32, 99, 111, 110, 110, 101, 99, 116, 101, 100];
    let b: [u8; 28] = [18, 30, 81, 6, 38, 27, 6, 86, 127, 1, 64, 67, 10, 51, 30, 84, 38, 4, 19, 1, 91, 29, 29, 86, 14, 22, 84, 29];
    let f: [u8; 28] = [
        a[0]  ^ b[0], 
        a[1]  ^ b[1], 
        a[2]  ^ b[2], 
        a[3]  ^ b[3], 
        a[4]  ^ b[4], 
        a[5]  ^ b[5], 
        a[6]  ^ b[6], 
        a[7]  ^ b[7], 
        a[8]  ^ b[8], 
        a[9]  ^ b[9], 
        a[10] ^ b[10], 
        a[11] ^ b[11], 
        a[12] ^ b[12], 
        a[13] ^ b[13], 
        a[14] ^ b[14], 
        a[15] ^ b[15], 
        a[16] ^ b[16], 
        a[17] ^ b[17], 
        a[18] ^ b[18], 
        a[19] ^ b[19], 
        a[20] ^ b[20], 
        a[21] ^ b[21], 
        a[22] ^ b[22], 
        a[23] ^ b[23], 
        a[24] ^ b[24], 
        a[25] ^ b[25], 
        a[26] ^ b[26], 
        a[27] ^ b[27], 
    ];
    // let f: [u8; 28] = [119, 104, 52, 116, 95, 116, 104, 51, 95, 104, 51, 99, 107, 95, 105, 53, 95, 119, 51, 98, 52, 115, 115, 51, 109, 98, 49, 121];

    set(&format!("Woah, how did you find a SHA256 hash collision? flag{{{}}}", unsafe { str::from_utf8_unchecked(&f) }));
}
#[wasm_bindgen]
pub fn check_hash(input: &str) {
    let input = input.as_bytes();
    let input_hash: [u8; 32] = Sha256::digest(input).into();

    let target = b"I've got a charm, I wanna put it on your heart, yeah / I wanna cry, I wanna multiply more times, yeah";
    let target_hash: [u8; 32] = hex!("6ca3e645abd9789ee26aec4344abeb2e8fe4b673a2f6ccb00d4092c01ef4e9ed");

    if input_hash != target_hash {
        let input_hash: String = input_hash
            .map(|c| format!("{:02x}", c))
            .into_iter()
            .collect();

        set(&format!("Good try! The hash of the input you provided was: <code>{}</code>", input_hash));
        return;
    }

    if input == target {
        set("Hey! You can't use the original text.");
        return;
    }

    print_flag();
}
