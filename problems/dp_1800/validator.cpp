#include <iostream>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cctype>
using namespace std;

// Simple validator: reads from stdin and checks format and constraints

int main(int argc, char* argv[]) {
    // 从文件读取
    FILE* f;
    if (argc > 1) {
        f = fopen(argv[1], "r");
        if (!f) {
            fprintf(stderr, "Cannot open file %s\n", argv[1]);
            return 1;
        }
    } else {
        f = stdin;
    }
    
    int n, k;
    if (fscanf(f, "%d %d", &n, &k) != 2) {
        fprintf(stderr, "Failed to read n and k\n");
        if (f != stdin) fclose(f);
        return 1;
    }
    
    // 验证范围
    if (n < 1 || n > 200000) {
        fprintf(stderr, "n out of range: %d\n", n);
        if (f != stdin) fclose(f);
        return 1;
    }
    if (k < 0 || k > 1000000000) {
        fprintf(stderr, "k out of range: %d\n", k);
        if (f != stdin) fclose(f);
        return 1;
    }
    
    for (int i = 0; i < n; i++) {
        int a;
        if (fscanf(f, "%d", &a) != 1) {
            fprintf(stderr, "Failed to read a[%d]\n", i);
            if (f != stdin) fclose(f);
            return 1;
        }
        if (a < 1 || a > 1000000000) {
            fprintf(stderr, "a[%d] out of range: %d\n", i, a);
            if (f != stdin) fclose(f);
            return 1;
        }
    }
    
    // 检查是否有多余字符
    int c;
    while ((c = fgetc(f)) != EOF) {
        if (!isspace(c)) {
            fprintf(stderr, "Extra character found after data\n");
            if (f != stdin) fclose(f);
            return 1;
        }
    }
    
    if (f != stdin) fclose(f);
    return 0;
}