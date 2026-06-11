#include "testlib.h"
#include <iostream>
using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    inf.init(argv[1], _input);
    
    int n = inf.readInt(1, 100000, "n");
    inf.readSpace();
    int k = inf.readInt(1, n, "k");
    inf.readSpace();
    long long d = inf.readLong(0LL, 1000000000LL, "d");
    inf.readEoln();
    
    for (int i = 0; i < n; i++) {
        long long a = inf.readLong(1LL, 1000000000LL, "a[i]");
        if (i + 1 < n) inf.readSpace();
    }
    inf.readEoln();
    
    inf.readEof();
    
    return 0;
}
