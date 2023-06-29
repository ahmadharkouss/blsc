import smartpy as sp

@sp.module
def main():
    class TournamentContract(sp.Contract):
        def __init__(self, owner):
            #Players 
            self.data.players =  sp.cast ({} , sp.map[sp.address, sp.int])
            #Winner
            self.data.winner=None
            #Status Value to prevent Cheating 
            self.data.isStarted = False
            #Entry fee of the tournament 
            self.data.entry_fee = sp.tez(100)
            #Owner of the tournament
            self.data.owner = owner
            #Keep track of # of tournaments: must always be one 
            self.data.id = sp.nat(0)

        @sp.onchain_view()
        def getPlayers(self):
            return  self.data.players
            
        @sp.onchain_view()
        def getStatus(self):
            return  self.data.isStarted    

        #Entry point that starts the tournament and do the transfer of money between the players and the contract.
        @sp.entry_point
        def start_tournament(self, PrizeContract_address):
            assert sp.sender == self.data.owner, "Only admin can start the tournament"
            status  =  sp.view("getStatus",PrizeContract_address, (),  sp.bool);
            assert status == sp.Some(False) , "Tournament finished, you can not start the tournament"
            assert self.data.isStarted == False, "Tournament already started"
            assert len(self.data.players) == 8, "Not enough players to start"
            self.data.id+=1
            self.data.isStarted = True
            #The entry point of the PrizeContract is called, the money is also transfered to the other contract.
            c = sp.contract(sp.unit,PrizeContract_address, entrypoint="add").unwrap_some()
            sp.transfer((), sp.balance, c)

        #Entry point that allows a player to join the tournament with one life.
        @sp.entry_point
        def join_tournament(self,PrizeContract_address):
            #Get the status of PrizeContract. 
            status  =  sp.view("getStatus",PrizeContract_address, (),  sp.bool);
            assert status == sp.Some(False) , "Tournament finished, you cannot join tournament"
            assert self.data.isStarted == False, "Not during the tournament"
            assert not self.data.players.contains(sp.sender), "Player has already joined the tournament"
            assert len(self.data.players) < 8, "Maximum number of players reached"
            assert sp.amount == self.data.entry_fee, "not rigth amount"
            assert self.data.id  ==0 , "You cannot join the tournament after declaring the winner"
            self.data.players[sp.sender] = sp.int(1)

        #Entry point that puts the number of life to zero to the player that has lost.
        @sp.entry_point
        def set_death(self, player,PrizeContract_address):
            assert sp.sender == self.data.owner, "Only admin can set who is dead"
            assert self.data.isStarted == True , "Tournament not started, you can not eliminate players"
            #Get the status of PrizeContract.
            status = sp.view("getStatus",PrizeContract_address, (),  sp.bool);
            assert status == sp.Some(False), "Tournament finished, you cannot eliminate players"
            #enough players
            assert sp.len(self.data.players)>=2, "You cannot eliminate, not enough players"
            #contain player
            assert self.data.players.contains(player), "Player not in the list"
            self.data.players[player] = 0
        
        #Entry point that updates the tournament with withdrawing player from the game.
        @sp.entry_point
        def update(self,PrizeContract_address):
            assert sp.sender == self.data.owner, "Only admin can update the tournament"
            #Get the status of PrizeContract.
            status  =  sp.view("getStatus",PrizeContract_address, (),  sp.bool);
            assert status == sp.Some(False) , "Tournament finished, you cannot update the game"
            assert self.data.isStarted == True, "Tournament not started, you can not update the game"
            
            assert len(self.data.players) > 2, "You cannot Update, there is already 2 finalists , proceed to declare winner"
            nbAlive = 0
            for player in self.data.players.keys():
                if self.data.players[player] == 1:
                    nbAlive += 1
            assert sp.mod(nbAlive,2) == 0, "Number of player alive should be even"
            #The players that have lost are removed from the map.
            for player in self.data.players.keys():
                if self.data.players[player] == 0:
                    del self.data.players[player]
        
        #Entry point that decalres the winner of the tournament.
        @sp.entry_point
        def declare_winner(self,PrizeContract_address):
            assert sp.sender == self.data.owner, "Only admin can declare the winner"
            #Get the status of PrizeContract.
            status  =  sp.view("getStatus",PrizeContract_address, (),  sp.bool);
            assert status == sp.Some(False) , "Tournament finished, you cannot declare a winner"
            assert self.data.isStarted == True, "Tournament not started, you cannot declare a winner"
            
            assert len(self.data.players) == 2, "Tournament still in progress, you can not declare a winner"
            assert self.data.winner == None, "Winner has already been declared"
            
            nbAlive = 0
            winner = None
            for player in self.data.players.keys():
                if self.data.players[player] == 1:
                    nbAlive += 1
                    winner = sp.Some(player)
            #Checking if there is still only one player in the game.
            assert nbAlive == 1, "Not only one alive"
            self.data.winner = winner
            #Tournament Finished
            self.data.isStarted = False
    
    class PrizeContract(sp.Contract):
        def __init__(self, owner):
            #Winner prize
            self.data.winner_prize= sp.tez(0)
            #Finalist prize
            self.data.finalist_prize= sp.tez(0)
            #Status Value to prevent Cheating 
            self.data.isFinished = False
            #Owner of the tournament
            self.data.owner = owner

        @sp.onchain_view()
        def getStatus(self):
            return  self.data.isFinished 

        @sp.entry_point
        def add(self):
            assert sp.amount == sp.tez(800), "not right amount"
            assert sp.balance == sp.tez(800), "error in transaction"
            
        #Owner can only set the prize if the tournament started and didn't finished  
        @sp.entry_point
        def set_prize_money(self, winner_prize, tournament_address):
            assert sp.sender == self.data.owner, "Only admin can set the prize money"
            assert winner_prize > sp.nat(50), "Prize for the winner should be more than 50%"

            #Checking if the tournament started and is not finished.
            status  =  sp.view("getStatus", tournament_address, (),  sp.bool);
            assert status == sp.Some(True) , "Tournament didn't start"
            assert self.data.isFinished == False , "Tournament finished cannot set the prize money"

            #Checking for correct amount of players.
            players = sp.view("getPlayers", tournament_address, (),  sp.map[sp.address, sp.int]).unwrap_some();
            assert len(players) == 8, "Incorrect amount of  players in the tournament"
            assert sp.balance == sp.tez(800), "Not the correct amount in the entry fee"
            nbAlive = 0
            for player in players.keys():
                if players[player] == 1:
                    nbAlive += 1
            assert nbAlive == 8, "Prize should be set when all players are alive"
            #The money of the contract is divided between the winner and the finalist.
            self.data.winner_prize = sp.split_tokens(sp.balance, winner_prize, sp.nat(100))
            self.data.finalist_prize = sp.split_tokens(sp.balance, sp.as_nat(sp.nat(100) - winner_prize), sp.nat(100))

        #Entry point that distributes the prize money to the winner.
        @sp.entry_point
        def distribute_prize_money_winner(self, tournament_address):
            assert sp.sender == self.data.owner, "Only admin can distribute the prize money"
            status  =  sp.view("getStatus", tournament_address, (),  sp.bool);
            assert status == sp.Some(False) , "You must declare a winner before distributing the money"
            assert self.data.isFinished == False, "Tournament already finished"
            self.data.isFinished = True
            players = sp.view("getPlayers", tournament_address,(), sp.map[sp.address, sp.int] ).unwrap_some();
            winner = None
            nbAlive = 0
            for player in players.keys():
                if players[player] == 1:
                    nbAlive += 1
                    winner = sp.Some(player)
            #Checking if there is still only one player in the game.
            assert nbAlive == 1, "Not only one alive"
            #The money is given to the winner.
            sp.send(winner.unwrap_some(), self.data.winner_prize)

        #Entry point that distributes the prize money to the finalist.
        @sp.entry_point
        def distribute_prize_money_finalist(self, tournament_address):
            assert sp.sender == self.data.owner, "Only admin can distribute the prize money"
            status  =  sp.view("getStatus", tournament_address, (),  sp.bool);
            assert status == sp.Some(False) , "You must declare a winner before distributing the money"
            assert self.data.isFinished == False, "Tournament already finished"
            players = sp.view("getPlayers", tournament_address,(), sp.map[sp.address, sp.int] ).unwrap_some();
            nbDead = 0
            finalist = None
            for player in players.keys():
                if players[player] == 0:
                    nbDead += 1
                    finalist = sp.Some(player)
            #Checking if there is still only one player in the game.
            assert nbDead == 1, "Not only one alive"
            #The money is given to the finalist.
            sp.send(finalist.unwrap_some(), self.data.finalist_prize)
            
           

@sp.add_test(name = "Testing")
def test():

    #-----------------------------------------------Scenario and contract initialisation---------------------------------------------------------------# 

    #Create the owner of the contract
    admin = sp.test_account("admin")
    scenario = sp.test_scenario(main)
    #Creating the tournament and assiging an owner to it
    tournament_contract = main.TournamentContract(owner = admin.address)
    prize_contract = main.PrizeContract(owner = admin.address)
    
    scenario += tournament_contract
    scenario += prize_contract
    
    #--------------------------------------------------------------------------------------------------------------------------------------------------#
    
    #Verify owners of the contracts
    scenario.verify(tournament_contract.data.owner == admin.address)
    scenario.verify(tournament_contract.data.owner == admin.address)

    #-------------------------------------Adding players to the tournament and testing edge Cases------------------------------------------------------#

    scenario.h2("1-Adding players")
    
    #Creating players accounts
    player1 = sp.test_account("player1")
    player2 = sp.test_account("player2")
    player3 = sp.test_account("player3")
    player4 = sp.test_account("player4")
    player5 = sp.test_account("player5")
    player6 = sp.test_account("player6")
    player7 = sp.test_account("player7")
    player8 = sp.test_account("player8")
    player9 = sp.test_account("player9")

    #Wrong entry fee
    scenario.h3("Wrong entry fee: accept only exact amount of fee: no return")
    
    scenario.h4("Greater than entry fee: should fail")
    tournament_contract.join_tournament(prize_contract.address).run(valid=False, sender=player1, amount = sp.tez(200))
    scenario.verify(sp.len(tournament_contract.data.players) == 0)
    #Verifying that the contract is not stealing money
    scenario.verify(tournament_contract.balance == sp.tez(0))
    
    scenario.h4("Lower than entry fee: : should fail")
    tournament_contract.join_tournament(prize_contract.address).run(valid=False, sender=player1, amount = sp.tez(50))
    scenario.verify(sp.len(tournament_contract.data.players) == 0)
    #Verifying that the contract is not stealing money
    scenario.verify(tournament_contract.balance == sp.tez(0))

    #Adding correct player 1 
    scenario.h3("Player 1 joined")
    tournament_contract.join_tournament(prize_contract.address).run(valid=True, sender=player1, amount = sp.tez(100))

    #Adding duplicate player 1
    scenario.h3("Testing duplicate player 1: should fail")
    tournament_contract.join_tournament(prize_contract.address).run(valid=False, sender=player1, amount = sp.tez(100))
    #Verifying that there is one player and not duplicates 
    scenario.verify(sp.len(tournament_contract.data.players) == 1)
    #Verifying the balance of the contract
    scenario.verify(tournament_contract.balance == sp.tez(100))

    #Adding Correct Player 2
    scenario.h3("Player 2 Joined")
    tournament_contract.join_tournament(prize_contract.address).run(valid=True, sender=player2, amount = sp.tez(100))
    #Verify the balance of the contract
    scenario.verify(tournament_contract.balance == sp.tez(200))
    #Verify the number of players
    scenario.verify(sp.len(tournament_contract.data.players) == 2)

    #Adding correct player 3
    scenario.h3("Player 3 joined")
    tournament_contract.join_tournament(prize_contract.address).run(valid=True, sender=player3, amount = sp.tez(100))
    #Verifying the balance of the contract
    scenario.verify(tournament_contract.balance == sp.tez(300))
    #Verify the number of players
    scenario.verify(sp.len(tournament_contract.data.players) == 3)

    #Adding correct player 4
    scenario.h3("Player 4 joined")
    tournament_contract.join_tournament(prize_contract.address).run(valid=True, sender=player4, amount = sp.tez(100))
    #Verify the balance of the contract
    scenario.verify(tournament_contract.balance == sp.tez(400))
    #Verify the number of players
    scenario.verify(sp.len(tournament_contract.data.players) == 4)

    #Adding correct player 5
    scenario.h3("Player 5 joined")
    tournament_contract.join_tournament(prize_contract.address).run(valid=True, sender=player5, amount = sp.tez(100))
    #Verifying the balance of the contract
    scenario.verify(tournament_contract.balance == sp.tez(500))
    #Verify the number of players
    scenario.verify(sp.len(tournament_contract.data.players) == 5)

    #Adding correct player 6
    scenario.h3("Player 6 joined")
    tournament_contract.join_tournament(prize_contract.address).run(valid=True, sender=player6, amount = sp.tez(100))
    #Verifying the balance of the contract
    scenario.verify(tournament_contract.balance == sp.tez(600))
    #Verify the number of players
    scenario.verify(sp.len(tournament_contract.data.players) == 6)

    #Adding correct player 7
    scenario.h3("Player 7 joined")
    tournament_contract.join_tournament(prize_contract.address).run(valid=True, sender=player7, amount = sp.tez(100))
    #Verifying the balance of the contract
    scenario.verify(tournament_contract.balance == sp.tez(700))
    #Verify the number of players
    scenario.verify(sp.len(tournament_contract.data.players) == 7)

    #Starting tournament with incorrect amount of  Players
    scenario.h3("Starting tournament with incorrect amount of players: should fail")
    tournament_contract.start_tournament(prize_contract.address).run(valid=False, sender = admin)
    scenario.verify(tournament_contract.data.isStarted == False)

    #Adding correct player 8
    scenario.h3("Player 8 joined")
    tournament_contract.join_tournament(prize_contract.address).run(valid=True, sender=player8, amount = sp.tez(100))
    #Verifying the balance of the contract
    scenario.verify(tournament_contract.balance == sp.tez(800))
    #Verify the number of players
    scenario.verify(sp.len(tournament_contract.data.players) == 8)

    #Adding pLayer 9 : too many players
    scenario.h3("Testing too many players joined the tournament: should fail")
    tournament_contract.join_tournament(prize_contract.address).run(valid=False, sender=player9, amount = sp.tez(100))
    #Verifying the balance of the contract
    scenario.verify(tournament_contract.balance == sp.tez(800))
    #Verify the number of players
    scenario.verify(sp.len(tournament_contract.data.players) == 8)

    scenario.h3("Setting winner prize before the tournament start: should fail")
    prize_contract.set_prize_money(winner_prize = sp.nat(70), tournament_address = tournament_contract.address).run(valid=False, sender = admin)
    
    #------------------------------------------Starting tournament and testing edge cases-----------------------------------------------------------------------------#

    scenario.h2("2-Starting tournament")

    scenario.h3("Only owner can start the tournament: should fail")
    tournament_contract.start_tournament(prize_contract.address).run(valid=False, sender = player1)
    scenario.verify(sp.len(tournament_contract.data.players) == 8)
    #Money should not be transfered to the PrizeContract in case of an error
    scenario.verify(tournament_contract.balance == sp.tez(800))

    scenario.h3("Owner started the tournament: transfering money to the other contract")
    tournament_contract.start_tournament(prize_contract.address).run(valid=True, sender = admin)
    scenario.verify(sp.len(tournament_contract.data.players) == 8)

    #Checking if the money is tranfered to the prize_contract
    scenario.verify(tournament_contract.balance == sp.tez(0))
    scenario.verify(prize_contract.balance == sp.tez(800))

    #Starting an already started tournament
    scenario.h3("owner can not start a tournament 2 times in a row: tournament not finished")
    tournament_contract.start_tournament(prize_contract.address).run(valid=False, sender = admin)
    scenario.verify(tournament_contract.balance == sp.tez(0))
    scenario.verify(prize_contract.balance == sp.tez(800))

    #Joining an already started tournament 
    scenario.h3("Joining an already started touranment: should fail")
    tournament_contract.join_tournament(prize_contract.address).run(valid=False, sender=player9, amount = sp.tez(100), exception = "Not during the tournament")

    #--------------------------------------Setting pourcentage prize to the winner and the finalist----------------------------------------------------------------
    
    scenario.h2("3-Owner setting pourcentage prize to the winner and the finalist")

    scenario.h3("Only owner allowed to set the winner prize : should fail")
    prize_contract.set_prize_money(winner_prize = sp.nat(70), tournament_address = tournament_contract.address).run(valid=False, sender = player1)
    scenario.verify(prize_contract.data.winner_prize == sp.tez(0))
    scenario.verify(prize_contract.data.finalist_prize == sp.tez(0))
    
    scenario.h3("Setting incorrect pourcentage for the winner < 50%")
    prize_contract.set_prize_money(winner_prize = sp.nat(10), tournament_address = tournament_contract.address).run(valid=False, sender = admin, exception ="Prize for the winner should be more than 50%")
    scenario.verify(prize_contract.data.winner_prize == sp.tez(0))
    scenario.verify(prize_contract.data.finalist_prize == sp.tez(0))
   
    scenario.h3("Setting incorrect pourcentage for the winner <= 50%")
    prize_contract.set_prize_money(winner_prize = sp.nat(50), tournament_address = tournament_contract.address).run(valid=False, sender = admin, exception ="Prize for the winner should be more than 50%")
    scenario.verify(prize_contract.data.winner_prize == sp.tez(0))
    scenario.verify(prize_contract.data.finalist_prize == sp.tez(0))

    scenario.h3("Setting correct pourcentage for the winner > 50%")
    prize_contract.set_prize_money(winner_prize = sp.nat(70), tournament_address = tournament_contract.address).run(valid=True, sender = admin )
    scenario.verify(prize_contract.data.winner_prize == sp.tez(560))
    scenario.verify(prize_contract.data.finalist_prize == sp.tez(240))

    #---------------------------------------------Eliminating players and updating tournament--------------------------------------------------------------------------------------#
        
    scenario.h2("4-Eliminating players and updating tournament")
    
    scenario.h3("Only owner can eliminate")
    tournament_contract.set_death(player=player1.address , PrizeContract_address=prize_contract.address).run(valid=True, sender = admin)

    scenario.h3("Eliminating player 1")
    tournament_contract.set_death(player=player1.address , PrizeContract_address=prize_contract.address).run(valid=True, sender = admin)
    
    scenario.h3("Eliminating player 2")
    tournament_contract.set_death(player=player2.address , PrizeContract_address=prize_contract.address).run(valid=True, sender = admin)
    scenario.h3("Eliminating player 3")
    tournament_contract.set_death(player=player3.address , PrizeContract_address=prize_contract.address).run(valid=True, sender = admin)

    scenario.h3("Not rigth amount of players alive(not even): should fail")
    tournament_contract.update(prize_contract.address).run(valid=False , sender = admin)

    scenario.h3("Eliminating player 4")
    tournament_contract.set_death(player=player4.address , PrizeContract_address=prize_contract.address).run(valid=True, sender = admin)

    scenario.h3("Updating tournament: even players alive")
    tournament_contract.update(prize_contract.address).run(valid=True , sender=admin)

    scenario.h3("Eliminating player 5")
    tournament_contract.set_death(player=player5.address , PrizeContract_address=prize_contract.address).run(valid=True, sender = admin)
    scenario.h3("Eliminating player 6")
    tournament_contract.set_death(player=player6.address , PrizeContract_address=prize_contract.address).run(valid=True, sender = admin)

    scenario.h3("Updating tournament: even players alive")
    tournament_contract.update(prize_contract.address).run(valid=True , sender=admin)

    scenario.h3("Updating tournament: should fail because only 2 players in the tournament")
    tournament_contract.update(prize_contract.address).run(valid=False)

    #-----------------------------------------Declaring the winner and finishing the contract-----------------------------------------------------------------------------------------#
        
    scenario.h2("5-Declaring the winner and finishing the contract")

    scenario.h3("Decalare winner: should fail because still two players alive")
    tournament_contract.declare_winner(prize_contract.address).run(valid=False , sender=admin)

    scenario.h3("Eliminating player 7")
    tournament_contract.set_death(player=player7.address , PrizeContract_address=prize_contract.address).run(valid=True, sender = admin)

    #Distributing prize money before declaring winner, should fail 
    scenario.h3("Distributing prize money before declaring winner, should fail")
    prize_contract.distribute_prize_money_winner(tournament_contract.address).run(sender = admin , valid=False)

    #Declaring winner
    scenario.h3("Decalaring winner: only one player alive")
    tournament_contract.declare_winner(prize_contract.address).run(valid=True , sender=admin)

    #Suspects players joining the game after declaring winner: should fail, one contract per tournament rule !
    scenario.h3("Suspects players joining the game after declaring winner: should fail")
    tournament_contract.join_tournament(prize_contract.address).run(valid=False, sender=player9, amount = sp.tez(100), exception="You cannot join the tournament after declaring the winner")

    #Duplicate declare winner: should fail

    scenario.h3("Duplicate declare winner: should fail")
    tournament_contract.declare_winner(prize_contract.address).run(valid=False, sender=admin)
    
    #Verifying that the winner is player8
    scenario.verify( (tournament_contract.data.winner)  == sp.some(player8.address) )
    
    scenario.h3("Distributing prize money to the finalist")
    prize_contract.distribute_prize_money_finalist(tournament_contract.address).run(sender = admin, valid=True)
    scenario.h3("Distributing prize money to the winner")
    prize_contract.distribute_prize_money_winner(tournament_contract.address).run(sender = admin, valid=True)
    #Verifying that the money has been sent
    scenario.verify(prize_contract.balance == sp.tez(0))
    
    #--------------------------------------------------Post tournament check------------------------------------------------------------------------------------------------#
    #                                            Approach one contract per tournament 

    scenario.h3("Contract already used , you cannot create new tournament: should fail")
    tournament_contract.start_tournament(prize_contract.address).run(valid=False, sender = admin)
    scenario.h3("Contract already used , you cannot declare winner: should fail")
    tournament_contract.declare_winner(prize_contract.address).run(valid=False, sender=admin)
    
    scenario.h3("Contract already used , player cannot join the tournament: should fail")
    tournament_contract.join_tournament(prize_contract.address).run(valid=False, sender=player1, amount = sp.tez(100))

    #..........