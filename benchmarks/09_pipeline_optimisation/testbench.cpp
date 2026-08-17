void kernel(const int in[256],int out[256]);
int main(){int in[256],out[256];for(int i=0;i<256;++i)in[i]=i-128;kernel(in,out);for(int i=0;i<256;++i)if(out[i]!=in[i]*3+7)return 1;return 0;}
