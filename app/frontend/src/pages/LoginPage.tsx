import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { client } from '@/lib/api';

export default function LoginPage() {
  const navigate = useNavigate();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    client.auth
      .me()
      .then((res) => {
        if (res?.data) {
          navigate('/');
        }
      })
      .catch(() => {})
      .finally(() => setChecking(false));
  }, []);

  if (checking) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-[#0C121C] via-[#0C121C] to-[#1a2535]">
      <Card className="w-full max-w-md mx-4 border-0 shadow-2xl bg-white/95 backdrop-blur">
        <CardHeader className="text-center pb-2">
          <div className="flex justify-center mb-4">
            <img src="/autohub-logo.png" alt="AutoHub" className="h-20 w-auto" />
          </div>
          <p className="text-muted-foreground mt-1 text-sm">
            Plataforma de Intermediação de Veículos
          </p>
        </CardHeader>
        <CardContent className="pt-4">
          <Button
            className="w-full bg-[#F16801] hover:bg-[#d45a01] text-white font-semibold text-base"
            size="lg"
            onClick={() => client.auth.toLogin()}
          >
            Entrar no Sistema
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}