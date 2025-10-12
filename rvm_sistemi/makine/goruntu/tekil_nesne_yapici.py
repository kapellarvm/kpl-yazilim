import threading

def Tekil(sinif):
    """
    Singleton (Tekil Nesne) tasarım desenini uygulayan bir decorator.
    Bu decorator ile işaretlenen bir sınıftan her zaman aynı nesne (instance) döner.
    Thread-safe (iş parçacığı-güvenli) yapıdadır.
    """
    nesneler = {}
    kilit = threading.Lock()

    def nesne_al(*args, **kwargs):
        # Çift kilit kontrolü ile aynı anda iki thread'in nesne oluşturmasını engeller.
        with kilit:
            if sinif not in nesneler:
                nesneler[sinif] = sinif(*args, **kwargs)
        return nesneler[sinif]

    return nesne_al
