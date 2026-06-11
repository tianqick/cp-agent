#include "testlib.h"
#include <iostream>
using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    inf.init(argv[1], _input);
    
    int n = inf.readInt(1, 5000, "n");
    inf.readEoln();
    
    for (int i = 0; i < n; i++) {
        inf.readInt(-1000000000, 1000000000, "a[i]");
        if (i + 1 < n) inf.readSpace();
    }
    inf.readEoln();
    inf.readEof();
    
    return 0;
}
