#include "testlib.h"
#include <iostream>
#include <string>
#include <vector>
using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    
    int idx = atoi(argv[1]);
    int total = atoi(argv[2]);
    
    int n;
    string s;
    
    if (idx <= 3) {
        // 小规模测试 (n <= 20)
        n = rnd.next(1, 20);
        s = "";
        for (int i = 0; i < n; i++) {
            int r = rnd.next(0, 2);
            if (r == 0) s += '(';
            else if (r == 1) s += ')';
            else s += '?';
        }
    } else if (idx <= 6) {
        // 中等规模 (n <= 100)
        n = rnd.next(20, 100);
        s = "";
        for (int i = 0; i < n; i++) {
            int r = rnd.next(0, 2);
            if (r == 0) s += '(';
            else if (r == 1) s += ')';
            else s += '?';
        }
    } else if (idx <= 10) {
        // 大规模 (n <= 1000)
        n = rnd.next(100, 1000);
        s = "";
        for (int i = 0; i < n; i++) {
            int r = rnd.next(0, 2);
            if (r == 0) s += '(';
            else if (r == 1) s += ')';
            else s += '?';
        }
    } else if (idx <= 15) {
        // 很大规模 (n <= 3000)
        n = rnd.next(1000, 3000);
        s = "";
        for (int i = 0; i < n; i++) {
            int r = rnd.next(0, 2);
            if (r == 0) s += '(';
            else if (r == 1) s += ')';
            else s += '?';
        }
    } else if (idx == 16) {
        // 边界：全是'?'，n为偶数
        n = rnd.next(2, 20) * 2; // 保证偶数
        s = string(n, '?');
    } else if (idx == 17) {
        // 边界：全是'?'，n为奇数（无法构成合法序列）
        n = rnd.next(1, 10) * 2 + 1;
        s = string(n, '?');
    } else if (idx == 18) {
        // 边界：全是'('，无法构成合法序列
        n = rnd.next(1, 20);
        s = string(n, '(');
    } else if (idx == 19) {
        // 边界：全是')'，无法构成合法序列
        n = rnd.next(1, 20);
        s = string(n, ')');
    } else if (idx == 20) {
        // 已经是合法括号序列
        n = rnd.next(2, 20) * 2;
        s = "";
        int open = 0;
        for (int i = 0; i < n; i++) {
            int remaining = n - i;
            if (open > 0 && (remaining - 1 < open || rnd.next(0, 1))) {
                s += ')';
                open--;
            } else {
                s += '(';
                open++;
            }
        }
    } else if (idx == 21) {
        // 很多'?'
        n = rnd.next(100, 500);
        s = "";
        for (int i = 0; i < n; i++) {
            if (rnd.next(1, 10) <= 8) {
                s += '?';
            } else {
                s += (rnd.next(0, 1) ? '(' : ')');
            }
        }
    } else if (idx == 22) {
        // 很少'?'
        n = rnd.next(100, 500);
        s = "";
        for (int i = 0; i < n; i++) {
            if (rnd.next(1, 100) <= 5) {
                s += '?';
            } else {
                s += (rnd.next(0, 1) ? '(' : ')');
            }
        }
    } else if (idx == 23) {
        // 交替的'('和')'加少量'?'
        n = rnd.next(100, 500);
        s = "";
        for (int i = 0; i < n; i++) {
            if (rnd.next(1, 20) <= 1) {
                s += '?';
            } else {
                s += (i % 2 == 0 ? '(' : ')');
            }
        }
    } else if (idx == 24) {
        // 边界：n=1
        n = 1;
        s = "?";
    } else if (idx == 25) {
        // 边界：n=2
        n = 2;
        if (rnd.next(0, 3) == 0) s = "()";
        else if (rnd.next(0, 2) == 0) s = "(?";
        else if (rnd.next(0, 1) == 0) s = "?)";
        else s = "??";
    } else if (idx == 26) {
        // 前半部分全是'('，后半部分全是'?' 
        n = rnd.next(100, 300);
        s = "";
        int half = n / 2;
        for (int i = 0; i < half; i++) s += '(';
        for (int i = half; i < n; i++) s += '?';
    } else if (idx == 27) {
        // 前半部分全是'?'，后半部分全是')'
        n = rnd.next(100, 300);
        s = "";
        int half = n / 2;
        for (int i = 0; i < half; i++) s += '?';
        for (int i = half; i < n; i++) s += ')';
    } else if (idx == 28) {
        // 嵌套括号加'?'
        n = rnd.next(100, 300);
        s = "";
        int depth = 0;
        for (int i = 0; i < n; i++) {
            if (depth == 0 || (depth > 0 && rnd.next(0, 3) == 0)) {
                if (rnd.next(1, 10) <= 2) {
                    s += '?';
                } else {
                    s += '(';
                    depth++;
                }
            } else {
                if (rnd.next(1, 10) <= 2) {
                    s += '?';
                } else {
                    s += ')';
                    depth--;
                }
            }
        }
    } else {
        // 随机大规模数据
        n = rnd.next(500, 3000);
        s = "";
        for (int i = 0; i < n; i++) {
            int r = rnd.next(0, 5);
            if (r <= 1) s += '(';
            else if (r <= 3) s += ')';
            else s += '?';
        }
    }
    
    // 输出n和字符串
    cout << n << endl;
    cout << s << endl;
    
    // 输出代价数组
    for (int i = 0; i < n; i++) {
        if (i > 0) cout << " ";
        cout << rnd.next(1, (int)1e9);
    }
    cout << endl;
    
    for (int i = 0; i < n; i++) {
        if (i > 0) cout << " ";
        cout << rnd.next(1, (int)1e9);
    }
    cout << endl;
    
    return 0;
}
