struct Packet { int data; bool last; };
void kernel(const Packet in[32], Packet out[32]);
int main() {
    Packet in[32] = {}, out[32] = {};
    for(int i=0;i<32;++i) in[i].data=i*7;
    kernel(in,out);
    for(int i=0;i<32;++i) if(out[i].data!=in[i].data+5 || out[i].last!=(i==31)) return 1;
    return 0;
}
