/* RPC-IC220 memory map.
 *
 * The rig's IO block (key / plaintext / ciphertext) lives in its own IOMEM
 * region at 0x30000000, deliberately NOT carved out of SRAM. An earlier version
 * reserved the low 0x100 bytes of SRAM for it, but an empty .data section never
 * advances the region pointer, so .bss silently fell back to ORIGIN(SRAM) and
 * landed on top of the IO block. Separate regions make that impossible.
 */
ENTRY(_start)

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 64K
    SRAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 8K
    IOMEM (rw)  : ORIGIN = 0x30000000, LENGTH = 4K
}

SECTIONS
{
    .text 0x08000000 :
    {
        KEEP(*(.text.entry))
        *(.text*)
        *(.rodata*)
        . = ALIGN(4);
    } > FLASH

    .data : AT (ADDR(.text) + SIZEOF(.text))
    {
        *(.data*)
        . = ALIGN(4);
    } > SRAM

    .bss (NOLOAD) :
    {
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
    } > SRAM

    _stack_top = ORIGIN(SRAM) + LENGTH(SRAM);

    /DISCARD/ : { *(.ARM.exidx*) *(.comment) }
}
