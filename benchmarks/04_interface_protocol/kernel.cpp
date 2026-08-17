struct Packet { int data; bool last; };
void kernel(const Packet in[32], Packet out[32]) {
    for (int i=0;i<32;++i) {
        out[i].data = in[i].data + 5;
        out[i].last = false;
    }
}
