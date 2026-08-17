void kernel(const int in[32], int out[32]);
int main(){int in[32],out[32];for(int i=0;i<32;++i)in[i]=i-8;kernel(in,out);for(int i=0;i<32;++i)if(out[i]!=in[i]*in[i]+3)return 1;return 0;}
