from app.supervisor import run_supervisor
import logging

logging.basicConfig(level=logging.INFO)

# A simple list of test cases, each with a query and an expected keyword in the response
TEST_CASES = [
    {
        "name": "SQL Agent Test",
        "query": "What is the outstanding balance for loan 2003?",
        "expected_keyword": "7,516" # Looking for the correct balance
    },
    {
        "name": "Policy Agent Test",
        "query": "What are the prepayment charges?",
        "expected_keyword": "foreclosure fee" # Looking for a key term from the policy
    },
    {
        "name": "Calculator Agent Test",
        "query": "If I have a loan of 50000 at 10% for 24 months, what happens if I prepay 10000?",
        "expected_keyword": "Reduce your EMI" # Looking for the calculator's output options
    },
    {
        "name": "SQL Fallback Test",
        "query": "What is the balance for loan 999999?",
        "expected_keyword": "couldn't find" # Looking for the fallback message
    }
]

def main():
    print("--- Running Integration Tests ---")
    all_passed = True
    for test in TEST_CASES:
        print(f"\nRunning test: {test['name']}...")
        result = run_supervisor(test["query"])
        final_response = result.get("final_response", "")
        
        if test["expected_keyword"] in final_response:
            print(f"PASSED: Found expected keyword '{test['expected_keyword']}'")
        else:
            print(f"FAILED: Did not find expected keyword '{test['expected_keyword']}'")
            print(f"   Agent Response: {final_response}")
            all_passed = False
            
    print("\n--- Integration Test Summary ---")
    if all_passed:
        print("All integration tests passed successfully!")
    else:
        print("Some integration tests failed.")

if __name__ == "__main__":
    main()