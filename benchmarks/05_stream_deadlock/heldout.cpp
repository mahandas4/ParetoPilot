#include <hls_stream.h>
void kernel(hls::stream<int>& in, hls::stream<int>& out);
int main() {
    hls::stream<int> in, out;
    for(int i=0;i<16;++i) in.write(100-i);
    kernel(in,out);
    if(out.size()!=16) return 1;
    for(int i=0;i<16;++i) if(out.read()!=102-i) return 1;
    return 0;
}
