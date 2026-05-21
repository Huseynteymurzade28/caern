import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/store/auth";
import { Globe2, Loader2 } from "lucide-react";

const schema = z
  .object({
    email: z.string().email("Geçerli bir e-posta girin"),
    username: z
      .string()
      .min(3, "Kullanıcı adı en az 3 karakter")
      .max(50, "Kullanıcı adı en fazla 50 karakter"),
    password: z.string().min(6, "Şifre en az 6 karakter"),
    confirm: z.string().min(6, "Şifreyi tekrar girin"),
  })
  .refine((d) => d.password === d.confirm, {
    message: "Şifreler eşleşmiyor",
    path: ["confirm"],
  });

type FormData = z.infer<typeof schema>;

export default function SignUp() {
  const navigate = useNavigate();
  const setTokens = useAuthStore((s) => s.setTokens);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  async function onSubmit(data: FormData) {
    try {
      const tokens = await authApi.register(data.email, data.username, data.password);
      setTokens(tokens.access_token, tokens.refresh_token);
      toast.success("Hesabınız oluşturuldu");
      navigate("/dashboard");
    } catch (err: any) {
      toast.error(err?.response?.data?.error?.message || "Kayıt başarısız");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(circle at center, rgba(0,212,255,0.08), transparent 70%)",
        }}
      />

      <div className="card-elev w-full max-w-sm p-8 relative z-10 shadow-glow">
        <div className="flex flex-col items-center mb-6">
          <div
            className="w-14 h-14 rounded-lg bg-gradient-to-br from-accent/30 to-accent/10
                          border border-accent/50 flex items-center justify-center mb-3 shadow-glow"
          >
            <Globe2 size={26} className="text-accent" />
          </div>
          <div className="text-2xl font-bold text-text-primary tracking-wide">CAERN</div>
          <div className="text-[10px] uppercase tracking-[0.25em] text-text-muted mt-1">
            Yeni Hesap Oluştur
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
          <div>
            <label className="label-sm block mb-1.5">E-posta</label>
            <input
              {...register("email")}
              type="email"
              className="input w-full"
              placeholder="you@example.com"
              autoComplete="email"
            />
            {errors.email && (
              <p className="text-cat-yikim text-xs mt-1">{errors.email.message}</p>
            )}
          </div>

          <div>
            <label className="label-sm block mb-1.5">Kullanıcı Adı</label>
            <input
              {...register("username")}
              type="text"
              className="input w-full"
              placeholder="kullanici_adi"
              autoComplete="username"
            />
            {errors.username && (
              <p className="text-cat-yikim text-xs mt-1">{errors.username.message}</p>
            )}
          </div>

          <div>
            <label className="label-sm block mb-1.5">Şifre</label>
            <input
              {...register("password")}
              type="password"
              className="input w-full"
              placeholder="••••••••"
              autoComplete="new-password"
            />
            {errors.password && (
              <p className="text-cat-yikim text-xs mt-1">{errors.password.message}</p>
            )}
          </div>

          <div>
            <label className="label-sm block mb-1.5">Şifre (Tekrar)</label>
            <input
              {...register("confirm")}
              type="password"
              className="input w-full"
              placeholder="••••••••"
              autoComplete="new-password"
            />
            {errors.confirm && (
              <p className="text-cat-yikim text-xs mt-1">{errors.confirm.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary w-full py-2.5 text-sm font-semibold"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={14} className="animate-spin" /> Hesap oluşturuluyor
              </>
            ) : (
              "Hesap Oluştur"
            )}
          </button>
        </form>

        <div className="mt-5 pt-4 border-t border-border-subtle text-center">
          <p className="text-xs text-text-muted">
            Zaten bir hesabın var mı?{" "}
            <Link to="/login" className="text-accent hover:underline">
              Giriş Yap
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
