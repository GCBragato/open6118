#pragma once
#include "equilibrium.h"
#include <functional>
#include <stdexcept>

namespace fco {

class SolverError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

// Brentq generico: encontra raiz de f(x)=0 em [a,b] com f(a)*f(b)<0.
// Mesmo algoritmo de scipy.optimize.brentq (scipy/optimize/Zeros/brentq.c),
// para paridade com o backend Python.
double brentq(
    const std::function<double(double)>& f,
    double a, double b,
    double xtol = 1e-4, double rtol = 1e-6, int maxiter = 100);

// Profundidade da LN (x_LN) tal que N(alpha, x_LN) == Nd. Amostra 40 pontos
// ate 5h e 20h; no dominio 5 o N so tende a reta b com x_LN -> infinito,
// entao segue com x_LN de 100h a 1e6 h (FCO-05).
double solve_x_LN(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double alpha, double Nd_kn, int n_grid,
    int n_sample = 40);

struct AlphaResult {
    double alpha;
    double x_LN;
    double Mx_kncm = 0.0;
    double My_kncm = 0.0;
    bool uniaxial = false;
};

// Plano ultimo com N = Nd e momento resistente na direcao
// theta_d = atan2(Myd, Mxd), COM SINAL (FCO-03): flexao normal com LN
// paralela ao eixo, faixa do quadrante e busca no circulo inteiro.
AlphaResult solve_direcao(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double Nd_kn, double theta_d, int n_grid);

// Compatibilidade: theta_d agora e atan2(Myd, Mxd) com sinal.
AlphaResult solve_alpha(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double Nd_kn, double theta_d, int n_grid);

}  // namespace fco
