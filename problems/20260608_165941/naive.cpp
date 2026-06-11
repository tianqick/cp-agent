#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <climits>
using namespace std;

typedef long long ll;
const ll INF = 1e18;

int n;
string s;
vector<ll> a, b;
ll ans;

// 检查字符串是否是合法括号序列
bool isValid(const string& t) {
    int cnt = 0;
    for (char c : t) {
        if (c == '(') cnt++;
        else cnt--;
        if (cnt < 0) return false;
    }
    return cnt == 0;
}

// 回溯法枚举所有'?'的选择
void dfs(int idx, ll cost, string& t) {
    if (idx == n) {
        if (isValid(t)) {
            ans = min(ans, cost);
        }
        return;
    }
    
    if (s[idx] == '?') {
        // 尝试变成'('
        t[idx] = '(';
        dfs(idx + 1, cost + a[idx], t);
        
        // 尝试变成')'
        t[idx] = ')';
        dfs(idx + 1, cost + b[idx], t);
        
        t[idx] = '?'; // 回溯
    } else {
        dfs(idx + 1, cost, t);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    cin >> n;
    cin >> s;
    
    a.resize(n);
    b.resize(n);
    for (int i = 0; i < n; i++) cin >> a[i];
    for (int i = 0; i < n; i++) cin >> b[i];
    
    // 统计'?'的数量，如果太多就用DP
    int qcount = 0;
    for (char c : s) {
        if (c == '?') qcount++;
    }
    
    // 如果'?'数量<=15，用暴力回溯
    if (qcount <= 15) {
        ans = INF;
        string t = s;
        dfs(0, 0, t);
        
        if (ans == INF) {
            cout << -1 << endl;
        } else {
            cout << ans << endl;
        }
    } else {
        // 否则用DP（和solution一样）
        vector<vector<ll>> dp(n + 1, vector<ll>(n + 1, INF));
        dp[0][0] = 0;
        
        for (int i = 0; i < n; i++) {
            for (int j = 0; j <= i; j++) {
                if (dp[i][j] == INF) continue;
                
                if (s[i] == '(') {
                    dp[i + 1][j + 1] = min(dp[i + 1][j + 1], dp[i][j]);
                } else if (s[i] == ')') {
                    if (j > 0) {
                        dp[i + 1][j - 1] = min(dp[i + 1][j - 1], dp[i][j]);
                    }
                } else {
                    dp[i + 1][j + 1] = min(dp[i + 1][j + 1], dp[i][j] + a[i]);
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
    }
    
    return 0;
}
