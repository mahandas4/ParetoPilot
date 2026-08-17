void kernel(const short matrix[64],const short vector[8],int out[8]);
int main(){short m[64],v[8];int o[8];for(int i=0;i<64;++i)m[i]=(i%2)?-2:5;for(int i=0;i<8;++i)v[i]=(i%3)-1;kernel(m,v,o);for(int r=0;r<8;++r){int e=0;for(int c=0;c<8;++c)e+=m[r*8+c]*v[c];if(o[r]!=e)return 1;}return 0;}
