from src.evals.cases_helper import CaseManager
import asyncio

if __name__ == "__main__":
    from src.evals.cases import cases
    case_manager = CaseManager(cases)
    try: 
        asyncio.run(case_manager.process_all_cases(threshold=95.0))
    except Exception as e:
        print(f"Error processing cases: {e}")
    finally: 
        case_manager.cleanup_temp_dir()

    # Save results to JSON files
    output_dir = "tests/evals"
    case_manager.save_results_to_json(output_dir)