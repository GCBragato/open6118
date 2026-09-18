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
double brentq(
    const std::function<double(double)>& f,
    double a, double b,
    double xtol = 1e-4, double rtol = 1e-6, int maxiter = 100);

// Profundidade da LN (x_LN) tal que N(alpha, x_LN) == Nd.
double solve_x_LN(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double alpha, double Nd_kn, int n_grid,
    int n_sample = 40);

// Inclinacao alpha tal que arctan(|My|/|Mx|) == theta_d.
// Retorna par (alpha, x_LN).
struct AlphaResult {
    double alpha;
    double x_LN;
};

AlphaResult solve_alpha(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double Nd_kn, double theta_d, int n_grid);

}  // namespace fco
