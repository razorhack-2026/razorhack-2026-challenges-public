import init, { check_hash } from "./pkg/wasm.js";
import { set } from "./helper.js"
await init()

document.getElementById("check-input").addEventListener("click", () => {
    const txt = document.getElementById("text-input").value;
    if (!txt) {
        set("The input is empty!")
        return;
    }
    check_hash(txt);
});
