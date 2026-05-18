import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/store/auth";
import { Globe2, Loader2 } from "lucide-react";

const schema = z.object({
  email: z.string().email("Geçerli bir e-posta girin"),
  password: z.string().min(6, "Şifre en az 6 karakter"),
});
type FormData = z.infer<typeof schema>;

export default function Login() {
  const navigate = useNavigate();
  const setTokens = useAuthStore((s) => s.setTokens);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  async function onSubmit(data: FormData) {
    try {
      const tokens = await authApi.login(data.email, data.password);
      setTokens(tokens.access_token, tokens.refresh_token);
      navigate("/dashboard");
    } catch (err: any) {
      toast.error(err?.response?.data?.error?.message || "Giriş başarısız");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Decorative gradient */}
      <div className="absolute inset-0 bg-gradient-radial from-accent/10 via-transparent to-transparent pointer-events-none"
           style={{ background: "radial-gradient(circle at center, rgba(0,212,255,0.08), transparent 70%)" }} />

      <div className="card-elev w-full max-w-sm p-8 relative z-10 shadow-glow">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-lg bg-gradient-to-br from-accent/30 to-accent/10
                          border border-accent/50 flex items-center justify-center mb-3 shadow-glow">
            <Globe2 size={26} className="text-accent" />
          </div>
          <div className="text-2xl font-bold text-text-primary tracking-wide">CAERN</div>
          <div className="text-[10px] uppercase tracking-[0.25em] text-text-muted mt-1">
            Geo Change Detection
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="label-sm block mb-2">E-posta</label>
            <input
              {...register("email")}
              type="email"
              className="input w-full"
              placeholder="you@example.com"
            />
            {errors.email && <p className="text-cat-yikim text-xs mt-1">{errors.email.message}</p>}
          </div>

          <div>
            <label className="label-sm block mb-2">Şifre</label>
            <input
              {...register("password")}
              type="password"
              className="input w-full"
              placeholder="••••••••"
            />
            {errors.password && <p className="text-cat-yikim text-xs mt-1">{errors.password.message}</p>}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary w-full py-2.5 text-sm font-semibold"
          >
            {isSubmitting ? <><Loader2 size={14} className="animate-spin" /> Giriş yapılıyor</> : "Giriş Yap"}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-border-subtle text-center">
          <p className="text-[10px] text-text-subtle font-mono">
            CAERN © 2026 — coğrafi değişim tespiti platformu
          </p>
        </div>
      </div>
    </div>
  );
}
