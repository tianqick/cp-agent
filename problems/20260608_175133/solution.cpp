#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

typedef long long ll;

ll gcd(ll a, ll b) {
    a = abs(a);
    b = abs(b);
    if (a == 0) return b;
    if (b == 0) return a;
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

struct BIT {
    int n;
    vector<ll> tree;
    BIT(int n) : n(n), tree(n + 1, 0) {}
    
    void update(int idx, ll val) {
        for (int i = idx; i <= n; i += i & (-i))
            tree[i] += val;
    }
    
    ll query(int idx) {
        ll sum = 0;
        for (int i = idx; i > 0; i -= i & (-i))
            sum += tree[i];
        return sum;
    }
};

struct SegTree {
    int n;
    vector<ll> tree;
    
    SegTree(int n) : n(n), tree(4 * n, 0) {}
    
    void update(int node, int start, int end, int idx, ll val) {
        if (start == end) {
            tree[node] += val;
            return;
        }
        int mid = (start + end) / 2;
        if (idx <= mid)
            update(2 * node, start, mid, idx, val);
        else
            update(2 * node + 1, mid + 1, end, idx, val);
        tree[node] = gcd(tree[2 * node], tree[2 * node + 1]);
    }
    
    ll query(int node, int start, int end, int l, int r) {
        if (l > r) return 0;
        if (l <= start && end <= r) return tree[node];
        int mid = (start + end) / 2;
        ll result = 0;
        if (l <= mid)
            result = gcd(result, query(2 * node, start, mid, l, r));
        if (r > mid)
            result = gcd(result, query(2 * node + 1, mid + 1, end, l, r));
        return result;
    }
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, q;
    cin >> n >> q;
    
    vector<ll> a(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }
    
    // 差分数组 b[i] = a[i] - a[i-1], a[0] = 0
    // 所以 b[1] = a[1], b[i] = a[i] - a[i-1] for i > 1
    
    BIT bit(n);
    SegTree seg(n);
    
    // 初始化
    for (int i = 1; i <= n; i++) {
        ll diff = a[i] - (i > 1 ? a[i - 1] : 0);
        bit.update(i, diff);
        seg.update(1, 1, n, i, diff);
    }
    
    while (q--) {
        int type;
        cin >> type;
        
        if (type == 1) {
            // 区间加法 [l, r] + x
            int l, r;
            ll x;
            cin >> l >> r >> x;
            
            // b[l] += x
            bit.update(l, x);
            seg.update(1, 1, n, l, x);
            
            // b[r+1] -= x (如果 r+1 <= n)
            if (r + 1 <= n) {
                bit.update(r + 1, -x);
                seg.update(1, 1, n, r + 1, -x);
            }
        } else {
            // 查询 [l, r] 的 GCD
            int l, r;
            cin >> l >> r;
            
            if (l == r) {
                // 只有一个元素，直接返回绝对值
                cout << abs(bit.query(l)) << "\n";
            } else {
                // gcd(a[l], a[l+1], ..., a[r])
                // = gcd(a[l], b[l+1], b[l+2], ..., b[r])
                ll al = bit.query(l);  // a[l]
                ll g = seg.query(1, 1, n, l + 1, r);  // gcd(b[l+1], ..., b[r])
                cout << gcd(al, g) << "\n";
            }
        }
    }
    
    return 0;
}