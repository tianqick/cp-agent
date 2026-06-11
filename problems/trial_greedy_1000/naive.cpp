#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, k;
    long long d;
    cin >> n >> k >> d;
    
    vector<long long> a(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }
    
    sort(a.begin(), a.end());
    
    // dp[i] = 最少分组数使得前i个学生都被分组
    vector<int> dp(n + 1, INT_MAX);
    dp[0] = 0;
    
    for (int i = 1; i <= n; i++) {
        for (int j = max(0, i - k); j < i; j++) {
            if (dp[j] == INT_MAX) continue;
            // 检查 a[j], a[j+1], ..., a[i-1] 是否可以作为一组
            if (a[i - 1] - a[j] <= d) {
                dp[i] = min(dp[i], dp[j] + 1);
            }
        }
    }
    
    cout << dp[n] << endl;
    
    return 0;
}
