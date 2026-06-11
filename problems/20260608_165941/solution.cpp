#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <climits>
using namespace std;

typedef long long ll;
const ll INF = 1e18;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    string s;
    cin >> s;
    
    vector<ll> a(n), b(n);
    for (int i = 0; i < n; i++) cin >> a[i];
    for (int i = 0; i < n; i++) cin >> b[i];
    
    // dp[i][j] = 前i个字符，当前有j个未匹配的左括号时的最小代价
    vector<vector<ll>> dp(n + 1, vector<ll>(n + 1, INF));
    dp[0][0] = 0;
    
    for (int i = 0; i < n; i++) {
        for (int j = 0; j <= i; j++) {
            if (dp[i][j] == INF) continue;
            
            if (s[i] == '(') {
                // 必须变成左括号
                dp[i + 1][j + 1] = min(dp[i + 1][j + 1], dp[i][j]);
            } else if (s[i] == ')') {
                // 必须变成右括号，需要有未匹配的左括号
                if (j > 0) {
                    dp[i + 1][j - 1] = min(dp[i + 1][j - 1], dp[i][j]);
                }
            } else {
                // '?' 可以选择变成左括号或右括号
                // 变成左括号
                dp[i + 1][j + 1] = min(dp[i + 1][j + 1], dp[i][j] + a[i]);
                // 变成右括号
                if (j > 0) {
                    dp[i + 1][j - 1] = min(dp[i + 1][j - 1], dp[i][j] + b[i]);
                }
            }
        }
    }
    
    if (dp[n][0] == INF) {
        cout << -1 << endl;
    } else {
        cout << dp[n][0] << endl;
    }
    
    return 0;
}
