#include "testlib.h"
#include <iostream>
#include <vector>
using namespace std;

typedef long long ll;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    inf.init(argv[1], _input);
    
    int n = inf.readInt(1, 200000, "n");
    inf.readSpace();
    int q = inf.readInt(1, 200000, "q");
    inf.readEoln();
    
    for (int i = 0; i < n; i++) {
        inf.readLong(1LL, 1000000000000LL, "a[i]");
        if (i + 1 < n) inf.readSpace();
    }
    inf.readEoln();
    
    for (int i = 0; i < q; i++) {
        int type = inf.readInt(1, 2, "type");
        inf.readSpace();
        int l = inf.readInt(1, n, "l");
        inf.readSpace();
        int r = inf.readInt(l, n, "r");
        
        if (type == 1) {
            inf.readSpace();
            inf.readLong(-1000000LL, 1000000LL, "x");
        }
        inf.readEoln();
    }
    
    inf.readEof();
    
    return 0;
}