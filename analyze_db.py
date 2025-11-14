"""
Script de análise do banco de dados SQLite
Útil para aprender e analisar os dados dos trades
"""
from database import Database
from datetime import datetime, timedelta
import json

def print_separator(title: str = ""):
    """Imprime separador visual"""
    print("\n" + "="*60)
    if title:
        print(f"  {title}")
        print("="*60)

def analyze_trades(db: Database):
    """Análise completa de trades"""
    print_separator("📊 ANÁLISE DE TRADES")
    
    # Estatísticas gerais
    stats = db.get_statistics()
    
    if not stats:
        print("❌ Nenhum trade encontrado no banco de dados")
        return
    
    print(f"\n📈 ESTATÍSTICAS GERAIS")
    print(f"  Total de trades: {stats['total_trades']}")
    print(f"  Trades vencedores: {stats['winning_trades']} ({stats['win_rate']:.2f}%)")
    print(f"  Trades perdedores: {stats['losing_trades']}")
    print(f"  PnL Total: ${stats['total_pnl_usdt']:.2f}")
    print(f"  PnL Médio: {stats['avg_pnl_pct']:.2f}%")
    print(f"  Melhor trade: {stats['best_trade_pct']:.2f}%")
    print(f"  Pior trade: {stats['worst_trade_pct']:.2f}%")
    
    # Por símbolo
    if stats.get('by_symbol'):
        print(f"\n📊 PERFORMANCE POR SÍMBOLO")
        for item in stats['by_symbol']:
            print(f"  {item['symbol']}:")
            print(f"    Trades: {item['trades']}")
            print(f"    PnL Total: ${item['pnl_usdt']:.2f}")
            print(f"    PnL Médio: {item['avg_pnl_pct']:.2f}%")
    
    # Últimos 10 trades
    print_separator("📋 ÚLTIMOS 10 TRADES")
    recent_trades = db.get_trades(limit=10)
    
    if recent_trades:
        print(f"{'ID':<5} {'Símbolo':<10} {'Entrada':<12} {'Saída':<12} {'PnL %':<10} {'PnL $':<12} {'Razão':<15}")
        print("-" * 80)
        for trade in recent_trades:
            print(f"{trade['id']:<5} {trade['symbol']:<10} ${trade['entry_price']:<11.8f} "
                  f"${trade['exit_price']:<11.8f} {trade['pnl_pct']:<9.2f}% "
                  f"${trade['pnl_usdt']:<11.2f} {trade['reason']:<15}")

def analyze_signals(db: Database):
    """Análise de sinais"""
    print_separator("🔔 ANÁLISE DE SINAIS")
    
    # Total de sinais
    all_signals = db.get_signals(limit=1000)
    executed_signals = db.get_signals(executed=True, limit=1000)
    not_executed = db.get_signals(executed=False, limit=1000)
    
    print(f"\n📊 ESTATÍSTICAS DE SINAIS")
    print(f"  Total de sinais: {len(all_signals)}")
    print(f"  Sinais executados: {len(executed_signals)} ({len(executed_signals)/len(all_signals)*100 if all_signals else 0:.1f}%)")
    print(f"  Sinais não executados: {len(not_executed)} ({len(not_executed)/len(all_signals)*100 if all_signals else 0:.1f}%)")
    
    # Últimos 10 sinais
    print_separator("📋 ÚLTIMOS 10 SINAIS")
    recent_signals = db.get_signals(limit=10)
    
    if recent_signals:
        print(f"{'ID':<5} {'Símbolo':<10} {'Tipo':<8} {'Preço':<12} {'Executado':<10} {'Trade ID':<10}")
        print("-" * 70)
        for signal in recent_signals:
            executed = "✅ Sim" if signal['executed'] else "❌ Não"
            trade_id = signal['trade_id'] if signal['trade_id'] else "-"
            print(f"{signal['id']:<5} {signal['symbol']:<10} {signal['signal_type']:<8} "
                  f"${signal['price']:<11.8f} {executed:<10} {trade_id:<10}")

def analyze_daily_performance(db: Database, days: int = 30):
    """Análise de performance diária"""
    print_separator(f"📅 PERFORMANCE DIÁRIA (Últimos {days} dias)")
    
    daily = db.get_daily_performance(days=days)
    
    if not daily:
        print("❌ Nenhum dado de performance diária encontrado")
        return
    
    print(f"\n{'Data':<12} {'Trades':<8} {'Win Rate':<10} {'PnL Total $':<15} {'PnL Médio %':<12}")
    print("-" * 70)
    
    for day in daily:
        print(f"{day['date']:<12} {day['total_trades']:<8} {day['win_rate']:<9.2f}% "
              f"${day['total_pnl_usdt']:<14.2f} {day['avg_pnl_pct']:<11.2f}%")
    
    # Resumo
    total_days = len(daily)
    total_trades = sum(d['total_trades'] for d in daily)
    total_pnl = sum(d['total_pnl_usdt'] for d in daily)
    avg_win_rate = sum(d['win_rate'] for d in daily) / total_days if total_days > 0 else 0
    
    print(f"\n📊 RESUMO ({days} dias):")
    print(f"  Dias com trades: {total_days}")
    print(f"  Total de trades: {total_trades}")
    print(f"  PnL Total: ${total_pnl:.2f}")
    print(f"  Win Rate Médio: {avg_win_rate:.2f}%")

def custom_queries(db: Database):
    """Exemplos de queries customizadas para aprendizado"""
    print_separator("🔍 QUERIES CUSTOMIZADAS (Exemplos)")
    
    # Query 1: Trades por razão de saída
    print("\n1️⃣ Trades por razão de saída:")
    result = db.execute_query('''
        SELECT reason, COUNT(*) as count, 
               SUM(pnl_usdt) as total_pnl,
               AVG(pnl_pct) as avg_pnl
        FROM trades
        GROUP BY reason
        ORDER BY count DESC
    ''')
    
    for row in result:
        print(f"  {row['reason']}: {row['count']} trades | "
              f"PnL Total: ${row['total_pnl']:.2f} | "
              f"PnL Médio: {row['avg_pnl']:.2f}%")
    
    # Query 2: Duração média dos trades
    print("\n2️⃣ Duração média dos trades:")
    result = db.execute_query('''
        SELECT 
            AVG(duration_seconds) as avg_duration,
            MIN(duration_seconds) as min_duration,
            MAX(duration_seconds) as max_duration
        FROM trades
        WHERE duration_seconds IS NOT NULL
    ''')
    
    if result:
        row = result[0]
        avg_min = row['avg_duration'] / 60 if row['avg_duration'] else 0
        min_min = row['min_duration'] / 60 if row['min_duration'] else 0
        max_min = row['max_duration'] / 60 if row['max_duration'] else 0
        print(f"  Média: {avg_min:.2f} minutos")
        print(f"  Mínima: {min_min:.2f} minutos")
        print(f"  Máxima: {max_min:.2f} minutos")
    
    # Query 3: Melhor e pior dia
    print("\n3️⃣ Melhor e pior dia:")
    result = db.execute_query('''
        SELECT date, total_pnl_usdt, total_trades
        FROM daily_performance
        ORDER BY total_pnl_usdt DESC
        LIMIT 1
    ''')
    
    if result:
        best = result[0]
        print(f"  Melhor dia: {best['date']} | PnL: ${best['total_pnl_usdt']:.2f} | Trades: {best['total_trades']}")
    
    result = db.execute_query('''
        SELECT date, total_pnl_usdt, total_trades
        FROM daily_performance
        ORDER BY total_pnl_usdt ASC
        LIMIT 1
    ''')
    
    if result:
        worst = result[0]
        print(f"  Pior dia: {worst['date']} | PnL: ${worst['total_pnl_usdt']:.2f} | Trades: {worst['total_trades']}")

def show_table_structure(db: Database):
    """Mostra estrutura das tabelas"""
    print_separator("🗄️ ESTRUTURA DO BANCO DE DADOS")
    
    tables = ['trades', 'signals', 'daily_performance', 'bot_configs']
    
    for table in tables:
        print(f"\n📋 Tabela: {table}")
        info = db.get_table_info(table)
        if info:
            print(f"  {'Coluna':<20} {'Tipo':<15} {'Nullable':<10}")
            print("  " + "-" * 50)
            for col in info:
                nullable = "Sim" if col['notnull'] == 0 else "Não"
                print(f"  {col['name']:<20} {col['type']:<15} {nullable:<10}")

def main():
    """Função principal"""
    print("\n" + "="*60)
    print("  🔍 ANALISADOR DE BANCO DE DADOS - BOT DE SCALPING")
    print("="*60)
    
    try:
        db = Database()
        
        # Menu interativo
        while True:
            print("\n📋 MENU DE ANÁLISES:")
            print("  1. Análise de Trades")
            print("  2. Análise de Sinais")
            print("  3. Performance Diária")
            print("  4. Queries Customizadas")
            print("  5. Estrutura do Banco")
            print("  6. Análise Completa")
            print("  0. Sair")
            
            choice = input("\nEscolha uma opção: ").strip()
            
            if choice == '1':
                analyze_trades(db)
            elif choice == '2':
                analyze_signals(db)
            elif choice == '3':
                days = input("Quantos dias? (padrão: 30): ").strip()
                days = int(days) if days.isdigit() else 30
                analyze_daily_performance(db, days)
            elif choice == '4':
                custom_queries(db)
            elif choice == '5':
                show_table_structure(db)
            elif choice == '6':
                analyze_trades(db)
                analyze_signals(db)
                analyze_daily_performance(db)
                custom_queries(db)
            elif choice == '0':
                print("\n👋 Até logo!")
                break
            else:
                print("❌ Opção inválida!")
    
    except FileNotFoundError:
        print("❌ Banco de dados não encontrado. Execute o bot primeiro para criar o banco.")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == '__main__':
    main()

