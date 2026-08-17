# Packet protocol

`kernel` receives 32 input packets and writes 32 output packets. Copy each payload after adding
five. Assert `last` on output index 31 only; it must be false for indices 0 through 30.
