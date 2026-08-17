#include <hls_stream.h>
void kernel(hls::stream<int>& in, hls::stream<int>& out) {
    for (int i=0;i<=16;++i) out.write(in.read()+2);
}
