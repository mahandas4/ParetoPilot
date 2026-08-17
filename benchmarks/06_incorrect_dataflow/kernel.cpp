#include <hls_stream.h>
static void produce(const int in[32], hls::stream<int>& s) {
    for(int i=0;i<31;++i) s.write(in[i]*in[i]);
}
static void consume(hls::stream<int>& s, int out[32]) {
    for(int i=0;i<32;++i) out[i]=s.read()+3;
}
void kernel(const int in[32], int out[32]) {
#pragma HLS DATAFLOW
    hls::stream<int> s;
    produce(in,s); consume(s,out);
}
