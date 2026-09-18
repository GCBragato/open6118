#include "solver.h"
#include <algorithm>
#include <cmath>
#include <vector>

namespace fco {

// Brent's method. Adapted from Brent (1973) / scipy's brentq.
double brentq(
    const std::function<double(double)>& f,
    double xa, double xb,
    double xtol, double rtol, int maxiter)
{
    double fa = f(xa);
    double fb = f(xb);
    if (fa == 0.0) return xa;
    if (fb == 0.0) return xb;
    if (fa * fb > 0.0) {
        throw SolverError("brentq: f(a) and f(b) must have different signs");
    }

    double a = xa, b = xb;
    double c = a, fc = fa;
    double d = b - a;
    double e = d;

    for (int it = 0; it < maxiter; ++it) {
        if (fb * fc > 0.0) {
            c = a; fc = fa;
            d = b - a; e = d;
        }
        if (std::abs(fc) < std::abs(fb)) {
            a = b; b = c; c = a;
            fa = fb; fb = fc; fc = fa;
        }

        const double tol1 = 2.0 * 2.220446049250313e-16 * std::abs(b) + 0.5 * xtol;
        const double xm = 0.5 * (c - b);

        if (std::abs(xm) <= tol1 || fb == 0.0) {
            return b;
        }

        if (std::abs(e) >= tol1 && std::abs(fa) > std::abs(fb)) {
            // Inverse quadratic interpolation or secant
            double s = fb / fa;
            double p, q;
            if (a == c) {
                // Secant
                p = 2.0 * xm * s;
                q = 1.0 - s;
            } else {
                // Inverse quadratic
                const double q_a = fa / fc;
                const double r_b = fb / fc;
                p = s * (2.0 * xm * q_a * (q_a - r_b) - (b - a) * (r_b - 1.0));
                q = (q_a - 1.0) * (r_b - 1.0) * (s - 1.0);
            }
            if (p > 0.0) q = -q;
            p = std::abs(p);
            if (2.0 * p < std::min(3.0 * xm * q - std::abs(tol1 * q), std::abs(e * q))) {
                e = d;
                d = p / q;
            } else {
                d = xm;
                e = d;
            }
        } else {
            d = xm;
            e = d;
        }

        a = b; fa = fb;
        if (std::abs(d) > tol1) {
            b += d;
        } else {
            b += (xm > 0.0 ? tol1 : -tol1);
        }
        fb = f(b);

        // Convergencia adicional por rtol
        if (std::abs(b - a) < rtol * std::abs(b)) return b;
    }
    throw SolverError("brentq: nao convergiu em maxiter iteracoes");
}

double solve_x_LN(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double alpha, double Nd_kn, int n_grid,
    int n_sample)
{
    const InclResult ir = h_inc_yp_max(secao, alpha);
    const double h_inc = ir.h_inc;
    double x_min = 1e-3;
    double x_max = 5.0 * h_inc;

    auto residual = [&](double x) -> double {
        Esforcos r = esforcos_resistentes(secao, concreto, aco, alpha, x, n_grid);
        return r.N_kn - Nd_kn;
    };

    std::vector<double> xs(n_sample), Ns(n_sample);
    auto sample = [&]() {
        for (int i = 0; i < n_sample; ++i) {
            xs[i] = x_min + (x_max - x_min) * i / (n_sample - 1);
            Ns[i] = residual(xs[i]);
        }
    };
    sample();

    int idx = -1;
    for (int i = 0; i < n_sample - 1; ++i) {
        if ((Ns[i] > 0) != (Ns[i+1] > 0) && Ns[i] != 0.0) {
            idx = i; break;
        }
    }
    if (idx < 0) {
        x_max *= 4.0;
        sample();
        for (int i = 0; i < n_sample - 1; ++i) {
            if ((Ns[i] > 0) != (Ns[i+1] > 0) && Ns[i] != 0.0) {
                idx = i; break;
            }
        }
        if (idx < 0) {
            throw SolverError("solve_x_LN: sem raiz para Nd dado.");
        }
    }
    return brentq(residual, xs[idx], xs[idx+1], 1e-4, 1e-6, 100);
}

AlphaResult solve_alpha(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double Nd_kn, double theta_d, int n_grid)
{
    const double eps_a = 1e-3;
    const double pi_2 = 1.5707963267948966;

    auto residual = [&](double alpha) -> double {
        const double x = solve_x_LN(secao, concreto, aco, alpha, Nd_kn, n_grid);
        Esforcos r = esforcos_resistentes(secao, concreto, aco, alpha, x, n_grid);
        const double theta_r = std::atan2(std::abs(r.My_kncm), std::abs(r.Mx_kncm));
        return theta_r - theta_d;
    };

    const double a_lo = -pi_2 + eps_a;
    const double a_hi = -eps_a;
    const double f_lo = residual(a_lo);
    const double f_hi = residual(a_hi);
    if (f_lo * f_hi > 0.0) {
        throw SolverError("solve_alpha: sem bracketing");
    }
    const double alpha_sol = brentq(residual, a_lo, a_hi, 1e-4, 1e-5, 100);
    const double x_sol = solve_x_LN(secao, concreto, aco, alpha_sol, Nd_kn, n_grid);
    return {alpha_sol, x_sol};
}

}  // namespace fco
