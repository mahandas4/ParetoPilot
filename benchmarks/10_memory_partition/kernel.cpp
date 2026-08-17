void kernel(const short matrix[64], const short vector[8], int out[8]) {
    for(int row=0;row<8;++row) {
        int acc=0;
        for(int col=0;col<8;++col) acc += matrix[row*8+col]*vector[col];
        out[row]=acc;
    }
}
