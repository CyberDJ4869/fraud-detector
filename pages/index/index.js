Page({
  data: {
    text: '',
    result: null,
    loading: false,
    // 定义多个可选API地址，便于在运行时切换
    apiUrls: [
      // 本地ngrok地址 - 需要根据最新生成替换
      'https://7141-223-67-100-192.ngrok-free.app/predict',
      // 备用本地IP地址（仅在同一WiFi网络内有效）
      'http://192.168.31.224:5000/predict'
    ],
    currentApiIndex: 0 // 当前使用的API索引
  },

  onLoad: function() {
    // 小程序加载时进行ping测试，确认API可用性
    this.pingApiEndpoints();
  },

  // 测试API端点是否可用
  pingApiEndpoints: function() {
    const pingPromises = this.data.apiUrls.map((url, index) => {
      return new Promise((resolve) => {
        const baseUrl = url.split('/predict')[0];
        console.log(`测试API端点 ${index+1}: ${baseUrl}`);
        
        wx.request({
          url: baseUrl,
          method: 'GET',
          timeout: 2000,
          success: () => resolve({ index, available: true }),
          fail: () => resolve({ index, available: false })
        });
      });
    });

    Promise.all(pingPromises).then(results => {
      const availableApi = results.find(result => result.available);
      if (availableApi) {
        console.log(`找到可用API: ${this.data.apiUrls[availableApi.index]}`);
        this.setData({ currentApiIndex: availableApi.index });
      } else {
        console.log('所有API端点均不可用');
      }
    });
  },

  onInput(e) {
    this.setData({
      text: e.detail.value
    });
  },

  // 切换到下一个API地址
  switchToNextApi: function() {
    const nextIndex = (this.data.currentApiIndex + 1) % this.data.apiUrls.length;
    console.log(`切换到下一个API: ${this.data.apiUrls[nextIndex]}`);
    this.setData({ currentApiIndex: nextIndex });
    return this.data.apiUrls[nextIndex];
  },

  onDetect() {
    // 检查是否有输入
    if (!this.data.text.trim()) {
      wx.showToast({
        title: '请输入短信内容',
        icon: 'none'
      });
      return;
    }
    
    // 设置加载状态
    this.setData({ loading: true });
    
    // 获取当前API地址
    const currentApiUrl = this.data.apiUrls[this.data.currentApiIndex];
    console.log('发送请求到:', currentApiUrl);
    console.log('请求数据:', { text: this.data.text });
    
    // 添加请求超时设置
    wx.request({
      url: currentApiUrl,
      method: 'POST',
      timeout: 10000, // 设置10秒超时
      header: {
        'content-type': 'application/json'
      },
      data: {
        text: this.data.text
      },
      success: res => {
        console.log('请求成功，响应数据:', res);
        
        if (res.statusCode === 200 && res.data.result !== undefined) {
          this.setData({
            result: res.data.result,
            loading: false
          });
        } else {
          console.error('接口返回异常数据:', res);
          this.setData({
            result: '接口异常',
            loading: false
          });
        }
      },
      fail: err => {
        console.error('请求失败:', err);
        
        // 如果是ngrok离线错误，尝试切换到下一个API
        if (err.errMsg && (err.errMsg.includes('offline') || 
            err.errMsg.includes('ERR_NGROK') || 
            err.errMsg.includes('timeout'))) {
          
          const nextApiUrl = this.switchToNextApi();
          wx.showToast({
            title: '正在切换线路...',
            icon: 'none',
            duration: 1500
          });
          
          // 延迟1.5秒后使用新API重试
          setTimeout(() => {
            this.onDetect();
          }, 1500);
          return;
        }
        
        wx.showToast({
          title: '请求失败，请检查网络',
          icon: 'none'
        });
        
        this.setData({
          result: '请求失败',
          loading: false
        });
      },
      complete: () => {
        // 在fail中如果触发重试，就不要立即清除loading状态
        if (this.data.loading) {
          console.log('请求完成');
        }
      }
    });
  }
}); 