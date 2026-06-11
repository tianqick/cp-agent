#include "testlib.h"
#include <iostream>
#include <string>
using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    inf.init(argv[1], _input);
    
    // 读取n
    int n = inf.readInt(1, 3000, "n");
    inf.readEoln();
    
    // 读取字符串s
    string s = inf.readLine();
    ensuref((int)s.length() == n, "String length must be n");
    for (char c : s) {
        ensuref(c == '(' || c == ')' || c == '?', "String must contain only '(', ')', '?'");
    }
    
    // 读取a数组
    for (int i = 0; i < n; i++) {
        if (i > 0) inf.readSpace();
        inf.readLong(1LL, 1000000000LL, "a[i]");
    }
    inf.readEoln();
    
    // 读取b数组
    for (int i = 0; i < n; i++) {
        if (i > 0) inf.readSpace();
        inf.readLong(1LL, 1000000000LL, "b[i]");
    }
    inf.readEoln();
    
    inf.readEof();
    
    return 0;
}
