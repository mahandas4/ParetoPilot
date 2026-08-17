double kernel(const float in[256]) {
    float sum = 0.0f;
    for (int i = 0; i < 256; ++i) sum += in[i];
    return sum;
}
