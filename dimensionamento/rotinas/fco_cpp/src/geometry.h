#pragma once
#include <vector>

namespace fco {

struct Barra {
    double x_cm;
    double y_cm;
    double area_cm2;
};

struct SecaoRetangular {
    double base_cm;
    double altura_cm;
    double cobrimento_cm;
    std::vector<Barra> barras;

    double Ac_cm2() const { return base_cm * altura_cm; }

    double As_total_cm2() const {
        double s = 0.0;
        for (const auto& b : barras) s += b.area_cm2;
        return s;
    }

    int n_barras() const { return static_cast<int>(barras.size()); }
};

// Inclinacao da fibra: alpha em rad
// Helpers: para uma secao retangular (centrada na origem), retorna:
//   h_inc = altura "inclinada" (max y - min y na direcao perpendicular a alpha)
//   yp_max = coordenada y' maxima da fibra mais comprimida
struct InclResult {
    double h_inc;
    double yp_max;
};

InclResult h_inc_yp_max(const SecaoRetangular& s, double alpha);

// Distancia inclinada: para a barra mais tracionada, distancia em relacao a fibra mais comprimida
double d_inc(const SecaoRetangular& s, double alpha, double yp_max);

}  // namespace fco
